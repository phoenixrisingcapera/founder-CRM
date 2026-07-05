from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import generate_id
from app.db.models import Deck, DeckExtractionRun, DeckFile, DeckSlide, DeckSlideAsset, DesignVersion, GeneratedSlide, SmartDeckWorkspace, WorkflowJob, WorkflowJobArtifact, WorkflowJobEvent
from app.services.failure_ticket_service import list_smart_deck_failure_events
from app.services.worker_runtime_status_service import get_latest_worker_heartbeat
from app.schemas.deck_workflow import (
    WorkflowApplyRequest,
    WorkflowExportRequest,
    WorkflowGenerationRequest,
    WorkflowLlmParallelizationRequest,
)
from app.services.export_service import create_export
from app.services.llm_parallelization_service import build_llm_parallelization_batches, summarize_parallelization_manifest
from app.services.deck_processing_queue_service import PROCESSING_RUN_TYPE
from app.services.smart_deck_llm_service import SmartDeckProviderUnavailableError, get_generation_provider_config
from app.services.workflow_job_service import (
    CLAIMABLE_JOB_STATUSES,
    JOB_STATUS_BLOCKED,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED_FINAL,
    JOB_STATUS_FAILED_RETRYABLE,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_TIMED_OUT,
    JOB_TYPE_APPLY_VERSION,
    JOB_TYPE_DB_PUBLISHER,
    JOB_TYPE_EXPORT,
    JOB_TYPE_LLM_GENERATION,
    JOB_TYPE_LLM_PARALLELIZATION,
    JOB_TYPE_SOURCE_INGESTION,
    JOB_TYPE_PREVIEW_RENDER,
    JOB_TYPE_SCHEMA_VALIDATION,
    JOB_TYPE_SOURCE_EXTRACTION,
    SOURCE_PIPELINE_JOB_SEQUENCE,
    ensure_pipeline_jobs_for_run,
    ensure_workflow_dependency,
    ensure_workflow_job,
    get_workflow_job_by_id,
    get_workflow_job_by_idempotency_key,
    list_workflow_jobs_for_deck,
    requeue_pipeline_jobs_for_run,
    set_workflow_job_status,
    workflow_job_dependencies_status,
    workflow_job_phase,
    workflow_job_progress,
)

WORKFLOW_READY_PHASES = {"smart_deck_ready", "preview_ready", "applied", "export_ready"}
SOURCE_PIPELINE_MAX_ATTEMPTS = 3


class WorkflowConflictError(ValueError):
    def __init__(self, *, code: str, message: str, recoverable: bool = True, next_action: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.recoverable = recoverable
        self.next_action = next_action


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_created_at(value: str | None) -> datetime:
    if not value:
        return datetime.min
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _coerce_mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _titleize_workflow_token(value: str) -> str:
    return " ".join(part[:1].upper() + part[1:] for part in value.split("_") if part)


def _workflow_status_to_phase_status(status: str) -> str:
    if status == "completed":
        return "completed"
    if status == "running":
        return "active"
    if status in {"failed_retryable", "failed_final", "blocked", "timed_out"}:
        return "failed"
    return "pending"


def _workflow_job_phases(jobs: list[WorkflowJob], active_job: WorkflowJob | None) -> list[dict[str, Any]]:
    latest_by_type: dict[str, WorkflowJob] = {}
    for job in jobs:
        if job.job_type not in latest_by_type:
            latest_by_type[job.job_type] = job

    ordered_job_types = [
        "source_ingestion",
        "source_extraction",
        "miniatures",
        "smart_deck_context",
        "db_publisher",
        "brand_extraction",
        "llm_generation",
        "llm_parallelization",
        "schema_validation",
        "preview_render",
        "apply_version",
        "export",
    ]

    active_job_type = active_job.job_type if active_job is not None else None
    phases: list[dict[str, Any]] = []
    for job_type in ordered_job_types:
        job = latest_by_type.get(job_type)
        if job is None and active_job_type == job_type and active_job is not None:
            job = active_job
        workflow_status = job.status if job is not None else "pending"
        phase_description = (
            workflow_job_phase(
                job.job_type,
                job.status,
                output_payload=_coerce_mapping(job.output_json),
            )
            if job is not None
            else None
        )
        phase_status = _workflow_status_to_phase_status(str(workflow_status))
        phases.append(
            {
                "key": job_type,
                "label": _titleize_workflow_token(job_type),
                "description": phase_description,
                "status": phase_status,
                "active": phase_status == "active",
                "completed": phase_status == "completed",
            }
        )
    return phases


def _workflow_missing_artifacts(
    *,
    source_file_saved: bool,
    source_extraction_ready: bool,
    thumbnail_count: int,
    generated_slide_count: int,
    renderable_schema_ready: bool,
    smart_deck_ready: bool,
) -> list[str]:
    missing: list[str] = []
    if not source_file_saved:
        missing.append("source_file")
    if source_file_saved and not source_extraction_ready:
        missing.append("extracted_structure")
    if source_extraction_ready and thumbnail_count <= 0:
        missing.append("slide_thumbnails")
    if smart_deck_ready and generated_slide_count <= 0:
        missing.append("generated_slides")
    if smart_deck_ready and not renderable_schema_ready:
        missing.append("renderable_schema")
    return missing


def _workflow_id(deck_id: str) -> str:
    return f"deckwf_{deck_id}"


def _provider_payload(db: Session, deck: Deck) -> dict[str, Any]:
    config = get_generation_provider_config(db, deck, None, strict=False, use_case="smart_deck")
    provider = str(config.get("provider") or "")
    api_key = config.get("apiKey")
    configured = provider not in {"", "missing", "missing_provider", "missing_openai", "missing_openrouter", "missing_claude", "fallback", "deterministic"} and bool(api_key)
    return {
        "configured": configured,
        "blockingReason": None if configured else "provider_not_configured",
        "provider": None if provider.startswith("missing") else provider,
        "model": config.get("model"),
    }


def _error_payload(code: str, message: str, *, recoverable: bool = True, next_action: str | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "recoverable": recoverable,
        "nextAction": next_action,
    }


def _normalized_generation_payload(payload: WorkflowGenerationRequest) -> dict[str, Any]:
    return {
        "prompt": payload.prompt.strip(),
        "selectedSourceSlideIds": list(payload.selectedSourceSlideIds),
        "sourceVersionId": payload.sourceVersionId,
        "styleId": payload.styleId,
        "brandProductId": payload.brandProductId,
        "additionalContext": payload.additionalContext,
        "deckType": payload.deckType,
        "audience": payload.audience,
        "preferredModel": payload.preferredModel,
        "selectedElementId": payload.selectedElementId,
        "selectedSubject": payload.selectedSubject,
        "actionId": payload.actionId,
        "actionPrompt": payload.actionPrompt,
        "userPrompt": payload.userPrompt,
        "latestBatchId": payload.latestBatchId,
        "detectedSubjects": payload.detectedSubjects,
        "subjectConfidence": payload.subjectConfidence,
    }


def _normalized_apply_payload(payload: WorkflowApplyRequest) -> dict[str, Any]:
    return {"designVersionId": payload.designVersionId}


def _normalized_export_payload(payload: WorkflowExportRequest) -> dict[str, Any]:
    export_type = (payload.normalized_type or "").strip()
    if not export_type:
        raise ValueError("export type is required")
    return {"exportType": export_type}


def _normalized_llm_parallelization_payload(payload: WorkflowLlmParallelizationRequest) -> dict[str, Any]:
    return {
        "prompt": payload.prompt.strip(),
        "selectedSourceSlideIds": list(payload.selectedSourceSlideIds),
        "partitionCount": int(payload.partitionCount),
        "batchSize": int(payload.batchSize),
        "preferredModel": payload.preferredModel,
    }


def _job_error(job: WorkflowJob) -> dict[str, Any] | None:
    if not job.error_message:
        return None
    recoverable = job.status == JOB_STATUS_FAILED_RETRYABLE
    next_action = "retry_job" if recoverable else "manual_review"
    return _error_payload(
        job.error_code or f"{job.job_type}_failed",
        job.error_message,
        recoverable=recoverable,
        next_action=next_action,
    )


def _job_retry_eligible(job: WorkflowJob) -> bool:
    return job.status == JOB_STATUS_FAILED_RETRYABLE and int(job.attempt_count or 0) < int(job.max_attempts or 0)


def _job_terminal(job: WorkflowJob) -> bool:
    return job.status in {
        JOB_STATUS_COMPLETED,
        JOB_STATUS_FAILED_FINAL,
        JOB_STATUS_BLOCKED,
        JOB_STATUS_TIMED_OUT,
    }


def _map_workflow_job_summary(job: WorkflowJob) -> dict[str, Any]:
    output = _coerce_mapping(job.output_json)
    phase = job.published_phase or workflow_job_phase(job.job_type, job.status, output_payload=output)
    return {
        "jobId": job.id,
        "jobType": job.job_type,
        "status": job.status,
        "phase": phase,
        "attemptCount": int(job.attempt_count or 0),
        "maxAttempts": int(job.max_attempts or 0),
        "recoveryCount": int(job.recovery_count or 0),
        "progress": workflow_job_progress(job.status),
        "queuedAt": _iso(job.queued_at or job.created_at),
        "startedAt": _iso(job.started_at),
        "heartbeatAt": _iso(job.heartbeat_at),
        "updatedAt": _iso(job.updated_at),
        "lockedUntil": _iso(job.locked_until),
        "lastRecoveredAt": _iso(job.last_recovered_at),
        "lastRecoveredBy": job.last_recovered_by,
        "completedAt": _iso(job.completed_at),
        "failedAt": _iso(job.failed_at),
        "publishedPhase": job.published_phase,
        "publishedAt": _iso(job.published_at),
        "workerId": job.locked_by,
        "terminal": _job_terminal(job),
        "terminalReason": job.terminal_reason,
        "retryEligible": _job_retry_eligible(job),
        "error": _job_error(job),
    }


def _map_workflow_job_artifact(artifact: WorkflowJobArtifact) -> dict[str, Any]:
    return {
        "artifactType": artifact.artifact_type,
        "artifactId": artifact.id,
        "storageKey": artifact.storage_key,
        "metadata": dict(artifact.metadata_json or {}),
    }


def _map_workflow_job_event(event: WorkflowJobEvent) -> dict[str, Any]:
    return {
        "eventType": event.event_type,
        "fromStatus": event.from_status,
        "toStatus": event.to_status or event.event_type,
        "message": event.message,
        "createdAt": _iso(event.created_at),
    }


def _latest_active_design_version(db: Session, deck_id: str) -> DesignVersion | None:
    return (
        db.query(DesignVersion)
        .filter(DesignVersion.deck_id == deck_id, DesignVersion.is_active.is_(True))
        .order_by(DesignVersion.updated_at.desc())
        .first()
    )


def _latest_completed_publisher(jobs: list[WorkflowJob]) -> WorkflowJob | None:
    for job in jobs:
        if job.job_type == JOB_TYPE_DB_PUBLISHER and job.status == JOB_STATUS_COMPLETED and job.published_phase:
            return job
    return None


def _latest_terminal_failure(jobs: list[WorkflowJob]) -> WorkflowJob | None:
    for job in jobs:
        if job.status in {JOB_STATUS_FAILED_RETRYABLE, JOB_STATUS_FAILED_FINAL, JOB_STATUS_BLOCKED, JOB_STATUS_TIMED_OUT}:
            return job
    return None


def _latest_completed_jobs_by_type(jobs: list[WorkflowJob]) -> dict[str, WorkflowJob]:
    latest: dict[str, WorkflowJob] = {}
    for job in jobs:
        if job.status == JOB_STATUS_COMPLETED and job.job_type not in latest:
            latest[job.job_type] = job
    return latest


def _source_enrichment_payload(completed_jobs_by_type: dict[str, WorkflowJob]) -> dict[str, Any] | None:
    def _source_enrichment_message(source: str | None, provider: str | None, llm_status: str | None) -> str:
        normalized_source = str(source or "").strip().lower()
        normalized_llm_status = str(llm_status or "").strip().lower()
        if normalized_source == "llm":
            return f"Validated source labels are attached{f' via {provider}' if provider else ''}."
        if normalized_source == "deterministic":
            return "Deterministic source labels are attached."
        if normalized_llm_status == "disabled":
            return "Source enrichment is disabled; deterministic labels are attached."
        if normalized_llm_status == "missing_provider":
            return "No enrichment provider was available; deterministic labels are attached."
        if normalized_llm_status == "invalid_llm_output":
            return "The enrichment output was rejected; deterministic labels are attached."
        if normalized_llm_status == "llm_failed":
            return "The enrichment step fell back to deterministic labels."
        return "Source-label readiness has not been reported yet."

    def _source_enrichment_badge(source: str | None, llm_status: str | None) -> str:
        normalized_source = str(source or "").strip().lower()
        normalized_llm_status = str(llm_status or "").strip().lower()
        if normalized_source == "llm" or normalized_llm_status == "llm_enriched":
            return "LLM-enriched source labels"
        if normalized_source == "deterministic":
            return "Deterministic source labels"
        if normalized_llm_status == "disabled":
            return "LLM enrichment disabled"
        if normalized_llm_status == "missing_provider":
            return "LLM provider missing"
        if normalized_llm_status == "invalid_llm_output":
            return "LLM output rejected"
        if normalized_llm_status == "llm_failed":
            return "LLM enrichment fallback"
        return "Source labels pending"

    for job_type in ("smart_deck_context", "source_extraction"):
        job = completed_jobs_by_type.get(job_type)
        if job is None:
            continue
        output = _coerce_mapping(job.output_json)
        source_enrichment = _coerce_mapping(output.get("sourceEnrichment"))
        if source_enrichment:
            source = source_enrichment.get("source")
            llm_status = source_enrichment.get("llmStatus")
            provider = source_enrichment.get("provider")
            return {
                "source": source,
                "llmStatus": llm_status,
                "provider": provider,
                "model": source_enrichment.get("model"),
                "badge": source_enrichment.get("badge") or _source_enrichment_badge(source, llm_status),
                "message": source_enrichment.get("message") or _source_enrichment_message(source, provider, llm_status),
            }
        source = output.get("enrichmentSource")
        llm_status = output.get("llmStatus")
        provider = output.get("llmProvider") or output.get("provider")
        model = output.get("llmModel") or output.get("model")
        if any(value not in {None, ""} for value in (source, llm_status, provider, model)):
            return {
                "source": source,
                "llmStatus": llm_status,
                "provider": provider,
                "model": model,
                "badge": _source_enrichment_badge(source, llm_status),
                "message": _source_enrichment_message(source, provider, llm_status),
            }
    return None


def _source_preview_payload(db: Session, deck_id: str) -> list[dict[str, Any]]:
    slides = (
        db.query(DeckSlide)
        .filter(DeckSlide.deck_id == deck_id)
        .order_by(DeckSlide.slide_index.asc())
        .limit(4)
        .all()
    )

    preview: list[dict[str, Any]] = []
    for slide in slides:
        blocks = sorted(slide.blocks or [], key=lambda item: int(item.block_index or 0))
        assets = sorted(slide.assets or [], key=lambda item: int(item.page_number or 0))
        preview.append(
            {
                "slideIndex": int(slide.slide_index or 0),
                "title": slide.title,
                "role": slide.role,
                "rawText": slide.raw_text,
                "sourcePageNumber": slide.source_page_number,
                "thumbnailPath": slide.thumbnail_path,
                "thumbnailMimeType": slide.thumbnail_mime_type,
                "widthPoints": slide.width_points,
                "heightPoints": slide.height_points,
                "metadata": dict(slide.metadata_json or {}),
                "blocks": [
                    {
                        "blockIndex": int(block.block_index or 0),
                        "rawText": block.raw_text,
                        "normalizedText": block.normalized_text,
                        "blockType": block.block_type,
                        "sourceKind": block.source_kind,
                        "metadata": dict(block.metadata_json or {}),
                    }
                    for block in blocks
                ],
                "assets": [
                    {
                        "assetType": asset.asset_type,
                        "label": asset.label,
                        "mimeType": asset.mime_type,
                        "assetUrl": asset.storage_path,
                        "pageNumber": asset.page_number,
                        "width": asset.width,
                        "height": asset.height,
                        "metadata": dict(asset.metadata_json or {}),
                    }
                    for asset in assets
                ],
            }
        )

    return preview


def _brand_state_payload(deck: Deck) -> dict[str, Any]:
    profile = deck.brand_profile
    if profile is None:
        return {
            "profileId": None,
            "status": "idle",
            "ready": False,
            "sourceMode": None,
            "profile": None,
        }

    status = profile.processing_status or "idle"
    ready = bool(profile.logo_url or (profile.palette_json and len(profile.palette_json) > 0) or profile.primary_color)
    if ready:
        status = "ready"
    elif status == "ready":
        status = "idle"

    return {
        "profileId": profile.id,
        "status": status,
        "ready": ready,
        "sourceMode": profile.source_mode,
        "profile": {
            "id": profile.id,
            "status": status,
            "companyName": profile.company_name,
            "companyWebsiteUrl": profile.company_website_url,
            "logoUrl": profile.logo_url,
            "faviconUrl": profile.favicon_url,
            "primaryColor": profile.primary_color,
            "secondaryColor": profile.secondary_color,
            "accentColor": profile.accent_color,
            "backgroundColor": profile.background_color,
            "textColor": profile.text_color,
            "palette": list(profile.palette_json or []),
            "fontCandidates": list(profile.font_candidates_json or []),
            "confidenceScore": profile.confidence_score,
            "sourceMode": profile.source_mode,
            "brandingJson": dict(profile.branding_json or {}) if profile.branding_json else None,
            "rawEvidence": dict(profile.raw_evidence_json or {}) if profile.raw_evidence_json else None,
            "warnings": list(profile.warnings_json or []),
            "updatedAt": profile.updated_at.isoformat() if profile.updated_at else None,
        },
    }


def _active_workflow_job(db: Session, jobs: list[WorkflowJob]) -> WorkflowJob | None:
    running_jobs = [job for job in jobs if job.status == JOB_STATUS_RUNNING]
    if running_jobs:
        running_jobs.sort(
            key=lambda job: (
                job.started_at or job.updated_at or job.created_at or datetime.min,
                job.created_at or datetime.min,
            ),
            reverse=True,
        )
        return running_jobs[0]

    queued_jobs = [job for job in jobs if job.status in CLAIMABLE_JOB_STATUSES]
    queued_jobs.sort(
        key=lambda job: (
            -(int(job.priority or 0)),
            job.created_at or datetime.min,
        ),
    )
    for job in queued_jobs:
        ready, blocked = workflow_job_dependencies_status(db, job)
        if ready and not blocked:
            return job
    return None


def _workflow_updated_at(
    *,
    jobs: list[WorkflowJob],
    deck_updated_at: datetime | None,
) -> str | None:
    candidates: list[datetime] = []
    for job in jobs[:25]:
        for value in (
            job.updated_at,
            job.completed_at,
            job.failed_at,
            job.heartbeat_at,
            job.started_at,
            job.queued_at,
            job.created_at,
        ):
            if value is not None:
                candidates.append(value)
                break
    if deck_updated_at is not None:
        candidates.append(deck_updated_at)
    if not candidates:
        return None
    return _iso(max(candidates))


def _lifecycle_status_from_phase(phase: str, workflow_status: str) -> str:
    if phase in {"smart_deck_ready", "preview_ready", "applied", "export_ready", "source_ready", "llm_parallelization_ready"}:
        return "ready"
    if workflow_status in {JOB_STATUS_FAILED_RETRYABLE, JOB_STATUS_FAILED_FINAL, JOB_STATUS_BLOCKED, JOB_STATUS_TIMED_OUT} or phase in {
        "failed_retryable",
        "failed_final",
        "needs_manual_review",
    }:
        return "failed"
    if phase in {
        "source_extraction_queued",
        "source_extraction_running",
        "miniatures_queued",
        "miniatures_running",
        "brand_extraction_queued",
        "brand_extraction_running",
        "smart_deck_context_queued",
        "smart_deck_context_running",
        "generation_queued",
        "generation_running",
        "llm_parallelization_queued",
        "llm_parallelization_running",
        "apply_queued",
        "apply_running",
        "export_queued",
        "export_running",
    } or workflow_status in {JOB_STATUS_QUEUED, JOB_STATUS_RUNNING}:
        return "processing"
    if phase in {"upload_accepted", "source_file_saved"}:
        return "queued"
    return "idle"


def _deck_extraction_status_from_phase(phase: str, workflow_status: str, source_file_saved: bool) -> str:
    if phase in {"source_ready", "smart_deck_ready", "preview_ready", "applied", "export_ready"}:
        return "ready"
    if phase in {
        "source_extraction_queued",
        "source_extraction_running",
        "miniatures_queued",
        "miniatures_running",
        "brand_extraction_queued",
        "brand_extraction_running",
        "smart_deck_context_queued",
        "smart_deck_context_running",
    } or workflow_status == JOB_STATUS_RUNNING:
        return "processing"
    if phase in {"upload_accepted"}:
        return "queued" if source_file_saved else "idle"
    if workflow_status in {JOB_STATUS_FAILED_RETRYABLE, JOB_STATUS_FAILED_FINAL, JOB_STATUS_BLOCKED, JOB_STATUS_TIMED_OUT} or phase in {
        "failed_retryable",
        "failed_final",
        "needs_manual_review",
    }:
        return "failed"
    return "queued" if source_file_saved else "idle"


def _terminal_workflow_status(status: str | None) -> bool:
    return status in {JOB_STATUS_FAILED_RETRYABLE, JOB_STATUS_FAILED_FINAL, JOB_STATUS_BLOCKED, JOB_STATUS_TIMED_OUT}


def get_deck_workflow_state(db: Session, deck_id: str) -> dict[str, Any] | None:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        return None

    deck_file = db.query(DeckFile).filter(DeckFile.deck_id == deck_id).one_or_none()
    workspace = db.query(SmartDeckWorkspace).filter(SmartDeckWorkspace.deck_id == deck_id).one_or_none()
    active_version = _latest_active_design_version(db, deck_id)
    jobs = list_workflow_jobs_for_deck(db, deck_id)
    latest_jobs = [_map_workflow_job_summary(job) for job in jobs[:10]]
    latest_jobs.sort(key=lambda item: _parse_created_at(item.get("queuedAt")), reverse=True)
    active_job_model = _active_workflow_job(db, jobs)
    active_job = _map_workflow_job_summary(active_job_model) if active_job_model is not None else None

    published_job = _latest_completed_publisher(jobs)
    failed_job = _latest_terminal_failure(jobs)
    published_phase = (
        published_job.published_phase
        or workflow_job_phase(
            published_job.job_type,
            published_job.status,
            output_payload=_coerce_mapping(published_job.output_json),
        )
        if published_job is not None
        else None
    )
    completed_jobs_by_type = _latest_completed_jobs_by_type(jobs)
    completed_job_types = set(completed_jobs_by_type)
    source_file_saved = deck_file is not None or "source_ingestion" in completed_job_types
    source_extraction_ready = bool(
        {"source_extraction", "miniatures", "brand_extraction", "smart_deck_context", "db_publisher"} & completed_job_types
    )
    brand_extraction_ready = "brand_extraction" in completed_job_types
    source_context_ready = bool({"smart_deck_context", "db_publisher"} & completed_job_types)
    renderable_schema_ready = bool(
        {"schema_validation", "preview_render", "apply_version", "export"} & completed_job_types
    )

    phase = "upload_accepted"
    workflow_status = JOB_STATUS_QUEUED
    if active_job is not None:
        phase = str(active_job["phase"])
        workflow_status = str(active_job.get("status") or JOB_STATUS_RUNNING)
    elif published_job is not None:
        phase = str(published_phase or "upload_accepted")
        workflow_status = published_job.status
    elif failed_job is not None:
        phase = workflow_job_phase(failed_job.job_type, failed_job.status, output_payload=_coerce_mapping(failed_job.output_json))
        workflow_status = failed_job.status
    elif source_file_saved:
        phase = "source_file_saved"
        workflow_status = JOB_STATUS_COMPLETED

    provider = _provider_payload(db, deck)
    published_ready_phase = str(published_phase or "")
    smart_deck_ready = published_ready_phase in {"smart_deck_ready", "preview_ready", "applied", "export_ready"}
    blocking_reason = None
    if active_job is None and failed_job is not None and not smart_deck_ready:
        blocking_reason = failed_job.error_code or failed_job.terminal_reason

    if phase in {"source_extraction_queued", "source_extraction_running", "miniatures_queued", "miniatures_running", "brand_extraction_queued", "brand_extraction_running", "smart_deck_context_queued", "smart_deck_context_running", "generation_queued", "generation_running", "llm_parallelization_queued", "llm_parallelization_running", "apply_queued", "apply_running"}:
        next_action = "view_processing"
    elif phase == "preview_ready":
        next_action = "apply_preview"
    elif phase == "applied":
        next_action = "open_smart_deck"
    elif phase in WORKFLOW_READY_PHASES:
        next_action = "open_smart_deck"
    elif failed_job is not None and failed_job.status == JOB_STATUS_FAILED_RETRYABLE:
        next_action = "retry_job"
    elif failed_job is not None:
        next_action = "view_processing"
    elif deck_file is None:
        next_action = "continue_upload"
    else:
        next_action = "view_processing"

    slide_count = db.query(DeckSlide).filter(DeckSlide.deck_id == deck_id).count()
    asset_count = db.query(DeckSlideAsset).filter(DeckSlideAsset.deck_id == deck_id).count()
    thumbnail_count = db.query(DeckSlide).filter(DeckSlide.deck_id == deck_id, DeckSlide.thumbnail_path.isnot(None)).count()
    generated_slide_count = db.query(GeneratedSlide).filter(GeneratedSlide.deck_id == deck_id).count()
    source_enrichment = _source_enrichment_payload(completed_jobs_by_type)
    brand_state = _brand_state_payload(deck)
    worker_heartbeat = get_latest_worker_heartbeat(db)
    failure_tickets = list_smart_deck_failure_events(db, deck_id=deck_id)

    source_context_job = completed_jobs_by_type.get("smart_deck_context")
    can_open_smart_deck = smart_deck_ready
    can_generate = can_open_smart_deck and provider["configured"]
    can_retry = failed_job is not None and failed_job.status == JOB_STATUS_FAILED_RETRYABLE and not smart_deck_ready
    degraded_mode = False
    if can_open_smart_deck:
        lifecycle_status = "ready"
    elif _terminal_workflow_status(workflow_status):
        lifecycle_status = "failed"
    elif not source_file_saved:
        lifecycle_status = "queued"
    else:
        lifecycle_status = "processing"
    deck_extraction_status = _deck_extraction_status_from_phase(phase, workflow_status, source_file_saved)
    phases = _workflow_job_phases(jobs, active_job_model)
    missing_artifacts = _workflow_missing_artifacts(
        source_file_saved=source_file_saved,
        source_extraction_ready=source_extraction_ready,
        thumbnail_count=thumbnail_count,
        generated_slide_count=generated_slide_count,
        renderable_schema_ready=renderable_schema_ready,
        smart_deck_ready=smart_deck_ready,
    )
    failures = list(failure_tickets.get("tickets") or [])

    source_version_id = None
    if source_context_job is not None:
        source_output = _coerce_mapping(source_context_job.output_json)
        source_version_id = source_output.get("sourceRunId")

    return {
        "deckId": deck.id,
        "workflowId": _workflow_id(deck.id),
        "phase": phase,
        "activeStage": phase,
        "status": workflow_status,
        "lifecycleStatus": lifecycle_status,
        "nextAction": next_action,
        "blockingReason": blocking_reason,
        "message": failed_job.error_message if failed_job is not None and active_job is None else None,
        "sourceFileStatus": "saved" if source_file_saved else "missing",
        "sourceFileSaved": source_file_saved,
        "deckExtractionStatus": deck_extraction_status,
        "processingStage": phase,
        "processingStageLabel": _titleize_workflow_token(phase),
        "workerState": active_job["status"] if active_job is not None else workflow_status,
        "workerMessage": failed_job.error_message if failed_job is not None and active_job is None else None,
        "retryUrl": f"/api/products/deck-aistack-codes/decks/{deck.id}/retry",
        "canRemove": False,
        "canOpenSmartDeck": can_open_smart_deck,
        "canGenerate": can_generate,
        "canRetry": can_retry,
        "degradedMode": degraded_mode,
        "missingArtifacts": missing_artifacts,
        "failures": failures,
        "workerHeartbeat": worker_heartbeat,
        "updatedAt": _workflow_updated_at(jobs=jobs, deck_updated_at=deck.updated_at),
        "activeJob": active_job,
        "latestJobs": latest_jobs[:5],
        "stages": phases,
        "phases": phases,
        "source": {
            "inputSourceId": deck_file.id if deck_file is not None else None,
            "sourceVersionId": source_version_id,
            "fileSaved": source_file_saved,
            "extractionReady": source_extraction_ready,
            "slideCount": slide_count,
            "assetCount": asset_count,
            "thumbnailCount": thumbnail_count,
            "brandExtractionReady": brand_extraction_ready,
            "sourceEnrichment": source_enrichment,
            "slides": _source_preview_payload(db, deck_id),
        },
        "smartDeck": {
            "workspaceId": workspace.id if workspace is not None else None,
            "ready": smart_deck_ready,
            "sourceSlideCount": slide_count,
            "generatedSlideCount": generated_slide_count,
            "activeDesignVersionId": active_version.id if active_version is not None else None,
            "hasRenderableSchema": renderable_schema_ready,
            "sourceContextReady": source_context_ready,
        },
        "provider": provider,
        "brand": brand_state,
        "links": {
            "processingUrl": f"/decks/{deck.id}/processing",
            "smartDeckUrl": f"/decks/{deck.id}/smart-deck",
        },
    }


def get_workflow_job(db: Session, job_id: str) -> dict[str, Any] | None:
    job = get_workflow_job_by_id(db, job_id)
    if job is None:
        return None

    summary = _map_workflow_job_summary(job)
    events = (
        db.query(WorkflowJobEvent)
        .filter(WorkflowJobEvent.job_id == job.id)
        .order_by(WorkflowJobEvent.created_at.asc())
        .all()
    )
    artifacts = (
        db.query(WorkflowJobArtifact)
        .filter(WorkflowJobArtifact.job_id == job.id)
        .order_by(WorkflowJobArtifact.created_at.asc())
        .all()
    )
    return {
        "jobId": summary["jobId"],
        "deckId": job.deck_id,
        "workflowId": _workflow_id(job.deck_id),
        "jobType": summary["jobType"],
        "status": summary["status"],
        "phase": summary["phase"],
        "attemptCount": summary["attemptCount"],
        "maxAttempts": summary["maxAttempts"],
        "recoveryCount": summary["recoveryCount"],
        "priority": int(job.priority or 0),
        "idempotencyKey": job.idempotency_key,
        "workerId": summary["workerId"],
        "progress": summary["progress"],
        "input": _coerce_mapping(job.input_json) or None,
        "output": _coerce_mapping(job.output_json) or None,
        "artifacts": [_map_workflow_job_artifact(artifact) for artifact in artifacts],
        "error": summary["error"],
        "queuedAt": summary["queuedAt"],
        "startedAt": summary["startedAt"],
        "heartbeatAt": summary["heartbeatAt"],
        "updatedAt": summary["updatedAt"],
        "lockedUntil": summary["lockedUntil"],
        "lastRecoveredAt": summary["lastRecoveredAt"],
        "lastRecoveredBy": summary["lastRecoveredBy"],
        "completedAt": summary["completedAt"],
        "failedAt": summary["failedAt"],
        "publishedPhase": summary["publishedPhase"],
        "publishedAt": summary["publishedAt"],
        "terminal": summary["terminal"],
        "terminalReason": summary["terminalReason"],
        "retryEligible": summary["retryEligible"],
        "events": [_map_workflow_job_event(event) for event in events],
    }

def _source_ingestion_job_for_checksum(db: Session, deck_id: str, source_checksum: str | None) -> WorkflowJob | None:
    if not source_checksum:
        return None
    return get_workflow_job_by_idempotency_key(
        db,
        deck_id=deck_id,
        job_type=JOB_TYPE_SOURCE_INGESTION,
        idempotency_key=f"{deck_id}:{source_checksum}:{JOB_TYPE_SOURCE_INGESTION}",
    )


def _source_checksum_from_run(run: DeckExtractionRun | None) -> str | None:
    if run is None or not isinstance(run.metadata_json, dict):
        return None
    raw = run.metadata_json.get("sourceChecksum")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _source_processing_run_metadata(
    *,
    deck: Deck,
    deck_file: DeckFile,
    source_checksum: str,
    requested_by_user_id: str | None,
    attempt_count: int = 0,
) -> dict[str, Any]:
    return {
        "requestedByUserId": requested_by_user_id,
        "sourceStoragePath": deck_file.storage_path,
        "sourceChecksum": source_checksum,
        "idempotencyKey": f"{deck.id}:{source_checksum}:{PROCESSING_RUN_TYPE}",
        "idempotencyScope": "deck_id_source_checksum_run_type",
        "stage": "source_saved",
        "stageLabel": "Source file saved",
        "nextAction": "wait_for_worker",
        "attemptCount": attempt_count,
        "maxAttempts": SOURCE_PIPELINE_MAX_ATTEMPTS,
        "heartbeatAt": datetime.utcnow().isoformat(),
    }


def _ensure_source_processing_run(
    db: Session,
    *,
    deck: Deck,
    deck_file: DeckFile,
    source_checksum: str,
    requested_by_user_id: str | None,
) -> DeckExtractionRun:
    ingestion_job = _source_ingestion_job_for_checksum(db, deck.id, source_checksum)
    if ingestion_job is not None and ingestion_job.extraction_run_id:
        workflow_run = (
            db.query(DeckExtractionRun)
            .filter(DeckExtractionRun.id == ingestion_job.extraction_run_id)
            .one_or_none()
        )
        if workflow_run is not None and _source_checksum_from_run(workflow_run) == source_checksum and workflow_run.source_file_id == deck_file.id:
            return workflow_run

    run = DeckExtractionRun(
        id=generate_id("process"),
        deck_id=deck.id,
        source_file_id=deck_file.id,
        run_type=PROCESSING_RUN_TYPE,
        extractor_name="workflow_source_pipeline",
        extractor_version="v2",
        source_format=deck_file.file_extension,
        status="queued",
        metadata_json=_source_processing_run_metadata(
            deck=deck,
            deck_file=deck_file,
            source_checksum=source_checksum,
            requested_by_user_id=requested_by_user_id,
        ),
    )
    db.add(run)
    db.flush()
    return run


def _requeue_source_processing_run(
    *,
    run: DeckExtractionRun,
    deck: Deck,
    deck_file: DeckFile,
    source_checksum: str,
    requested_by_user_id: str | None,
) -> None:
    run.status = "queued"
    run.started_at = None
    run.completed_at = None
    run.error_message = None
    run.source_file_id = deck_file.id
    run.source_format = deck_file.file_extension
    run.extractor_name = "workflow_source_pipeline"
    run.extractor_version = "v2"
    run.metadata_json = _source_processing_run_metadata(
        deck=deck,
        deck_file=deck_file,
        source_checksum=source_checksum,
        requested_by_user_id=requested_by_user_id,
        attempt_count=0,
    )


def _sync_source_processing_run_from_jobs(
    *,
    run: DeckExtractionRun,
    deck: Deck,
    deck_file: DeckFile,
    source_checksum: str,
    requested_by_user_id: str | None,
    jobs: dict[str, WorkflowJob],
) -> WorkflowJob | None:
    head_job = None
    for job_type in SOURCE_PIPELINE_JOB_SEQUENCE:
        candidate = jobs.get(job_type)
        if candidate is not None and candidate.status != JOB_STATUS_COMPLETED:
            head_job = candidate
            break
    if head_job is None:
        head_job = jobs.get(JOB_TYPE_DB_PUBLISHER) or jobs.get(JOB_TYPE_SOURCE_EXTRACTION) or jobs.get(JOB_TYPE_SOURCE_INGESTION)

    attempt_count = 0
    for candidate in jobs.values():
        attempt_count = max(attempt_count, int(candidate.attempt_count or 0))

    metadata = _source_processing_run_metadata(
        deck=deck,
        deck_file=deck_file,
        source_checksum=source_checksum,
        requested_by_user_id=requested_by_user_id,
        attempt_count=attempt_count,
    )
    if head_job is not None:
        metadata.update(
            {
                "workflowJobId": head_job.id,
                "workflowJobType": head_job.job_type,
                "workflowJobStatus": head_job.status,
            }
        )
    run.metadata_json = metadata

    has_running = any(candidate.status == JOB_STATUS_RUNNING for candidate in jobs.values())
    has_unfinished = any(candidate.status != JOB_STATUS_COMPLETED for candidate in jobs.values())
    if has_running:
        run.status = "processing"
        run.started_at = run.started_at or datetime.utcnow()
        run.completed_at = None
        run.error_message = None
    elif has_unfinished:
        run.status = "queued"
        run.completed_at = None
        run.error_message = None
    else:
        run.status = "completed"
        run.completed_at = run.completed_at or datetime.utcnow()
        run.error_message = None

    return head_job


def _ensure_generation_pipeline_jobs(
    db: Session,
    *,
    deck: Deck,
    generation_job: WorkflowJob,
    idempotency_key: str,
    current_user_id: str,
) -> tuple[WorkflowJob, WorkflowJob, WorkflowJob]:
    schema_validation_job = ensure_workflow_job(
        db,
        deck=deck,
        job_type=JOB_TYPE_SCHEMA_VALIDATION,
        status=JOB_STATUS_QUEUED,
        idempotency_key=f"{idempotency_key}:schema-validation",
        max_attempts=1,
        input_payload={
            "generationWorkflowJobId": generation_job.id,
            "requestedByUserId": current_user_id,
        },
    )
    preview_render_job = ensure_workflow_job(
        db,
        deck=deck,
        job_type=JOB_TYPE_PREVIEW_RENDER,
        status=JOB_STATUS_QUEUED,
        idempotency_key=f"{idempotency_key}:preview-render",
        max_attempts=1,
        input_payload={
            "generationWorkflowJobId": generation_job.id,
            "schemaValidationWorkflowJobId": schema_validation_job.id,
            "requestedByUserId": current_user_id,
        },
    )
    publisher_job = ensure_workflow_job(
        db,
        deck=deck,
        job_type=JOB_TYPE_DB_PUBLISHER,
        status=JOB_STATUS_QUEUED,
        idempotency_key=f"{idempotency_key}:publisher",
        max_attempts=1,
        input_payload={
            "publishTarget": "preview_ready",
            "generationWorkflowJobId": generation_job.id,
            "schemaValidationWorkflowJobId": schema_validation_job.id,
            "previewRenderWorkflowJobId": preview_render_job.id,
            "requestedByUserId": current_user_id,
        },
    )
    ensure_workflow_dependency(db, job=schema_validation_job, depends_on_job=generation_job)
    ensure_workflow_dependency(db, job=preview_render_job, depends_on_job=schema_validation_job)
    ensure_workflow_dependency(db, job=publisher_job, depends_on_job=preview_render_job)
    return schema_validation_job, preview_render_job, publisher_job


def queue_source_extraction(db: Session, deck_id: str, *, requested_by_user_id: str | None) -> dict[str, Any]:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        raise ValueError("Deck not found")
    deck_file = db.query(DeckFile).filter(DeckFile.deck_id == deck_id).one_or_none()
    if deck_file is None:
        raise ValueError("Deck source file not found")
    source_checksum = str(deck_file.checksum_sha256 or "").strip()
    if not source_checksum:
        raise ValueError("Deck source checksum is required for idempotent processing")

    run = _ensure_source_processing_run(
        db,
        deck=deck,
        deck_file=deck_file,
        source_checksum=source_checksum,
        requested_by_user_id=requested_by_user_id,
    )
    jobs = ensure_pipeline_jobs_for_run(
        db,
        deck=deck,
        run=run,
        source_checksum=source_checksum,
        max_attempts=SOURCE_PIPELINE_MAX_ATTEMPTS,
    )

    if any(
        job.status in {JOB_STATUS_FAILED_RETRYABLE, JOB_STATUS_FAILED_FINAL, JOB_STATUS_BLOCKED, JOB_STATUS_TIMED_OUT}
        for job in jobs.values()
    ):
        _requeue_source_processing_run(
            run=run,
            deck=deck,
            deck_file=deck_file,
            source_checksum=source_checksum,
            requested_by_user_id=requested_by_user_id,
        )
        jobs = requeue_pipeline_jobs_for_run(
            db,
            deck=deck,
            run=run,
            source_checksum=source_checksum,
            max_attempts=SOURCE_PIPELINE_MAX_ATTEMPTS,
        )

    accepted_job = _sync_source_processing_run_from_jobs(
        run=run,
        deck=deck,
        deck_file=deck_file,
        source_checksum=source_checksum,
        requested_by_user_id=requested_by_user_id,
        jobs=jobs,
    )

    ingestion_job = jobs.get(JOB_TYPE_SOURCE_INGESTION)
    source_job = jobs.get(JOB_TYPE_SOURCE_EXTRACTION)
    active_source_pipeline = (
        (ingestion_job is not None and ingestion_job.status != JOB_STATUS_COMPLETED)
        or (source_job is not None and source_job.status != JOB_STATUS_COMPLETED)
    )

    if active_source_pipeline and deck.status != "processing":
        from app.services.deck_state_machine_service import DeckState, transition_deck_state

        transition_deck_state(
            db,
            deck,
            DeckState.PROCESSING,
            actor_user_id=requested_by_user_id,
            reason="workflow_source_pipeline_queued",
            summary="Deck processing has been queued through workflow jobs.",
            source_surface="deck_workflow_service",
            source_route=f"/decks/{deck_id}/workflow",
            metadata={
                "processingRunId": run.id,
                "sourceChecksum": source_checksum,
                "workflowJobId": accepted_job.id if accepted_job is not None else None,
                "workflowJobType": accepted_job.job_type if accepted_job is not None else None,
            },
        )

    db.commit()

    refreshed_jobs = ensure_pipeline_jobs_for_run(
        db,
        deck=deck,
        run=run,
        source_checksum=source_checksum,
        max_attempts=SOURCE_PIPELINE_MAX_ATTEMPTS,
    )
    accepted_job = None
    for job_type in SOURCE_PIPELINE_JOB_SEQUENCE:
        candidate = refreshed_jobs.get(job_type)
        if candidate is not None and candidate.status != JOB_STATUS_COMPLETED:
            accepted_job = candidate
            break
    if accepted_job is None:
        accepted_job = refreshed_jobs.get(JOB_TYPE_DB_PUBLISHER) or refreshed_jobs.get(JOB_TYPE_SOURCE_EXTRACTION)
    if accepted_job is None:
        raise ValueError("Workflow source extraction job was not created")
    summary = _map_workflow_job_summary(accepted_job)
    return {
        "accepted": True,
        "jobId": accepted_job.id,
        "jobType": accepted_job.job_type,
        "status": summary["status"],
        "phase": summary["phase"],
        "workflowStateUrl": f"/api/products/deck-aistack-codes/decks/{deck_id}/workflow-state",
        "jobUrl": f"/api/workflow-jobs/{accepted_job.id}",
    }


def queue_smart_deck_generation(db: Session, deck_id: str, *, current_user_id: str, payload: WorkflowGenerationRequest) -> dict[str, Any]:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        raise ValueError("Deck not found")
    workflow_state = get_deck_workflow_state(db, deck_id)
    current_phase = str((workflow_state or {}).get("phase") or "")
    if current_phase not in {"smart_deck_ready", "preview_ready", "applied", "export_ready"}:
        raise WorkflowConflictError(
            code="smart_deck_not_ready",
            message="Finish source processing before starting Smart Deck generation.",
            recoverable=True,
            next_action="view_processing",
        )
    try:
        get_generation_provider_config(db, deck, payload.preferredModel, strict=True, use_case="smart_deck")
    except SmartDeckProviderUnavailableError as exc:
        raise WorkflowConflictError(
            code="provider_not_configured",
            message="Connect an AI provider before generating Smart Deck previews.",
            recoverable=True,
            next_action="configure_provider",
        ) from exc

    normalized_input = _normalized_generation_payload(payload)
    existing = get_workflow_job_by_idempotency_key(
        db,
        deck_id=deck_id,
        job_type=JOB_TYPE_LLM_GENERATION,
        idempotency_key=payload.idempotencyKey,
    )
    if existing is not None:
        _ensure_generation_pipeline_jobs(
            db,
            deck=deck,
            generation_job=existing,
            idempotency_key=payload.idempotencyKey,
            current_user_id=current_user_id,
        )
        if _coerce_mapping(existing.input_json) != normalized_input:
            raise WorkflowConflictError(
                code="idempotency_key_conflict",
                message="The idempotency key is already bound to a different Smart Deck generation request.",
                recoverable=False,
            )
        summary = _map_workflow_job_summary(existing)
        return {
            "accepted": True,
            "jobId": existing.id,
            "jobType": existing.job_type,
            "status": summary["status"],
            "phase": summary["phase"],
            "workflowStateUrl": f"/api/products/deck-aistack-codes/decks/{deck_id}/workflow-state",
            "jobUrl": f"/api/workflow-jobs/{existing.id}",
        }

    generation_job = ensure_workflow_job(
        db,
        deck=deck,
        job_type=JOB_TYPE_LLM_GENERATION,
        status=JOB_STATUS_QUEUED,
        idempotency_key=payload.idempotencyKey,
        max_attempts=2,
        input_payload=normalized_input,
    )
    _ensure_generation_pipeline_jobs(
        db,
        deck=deck,
        generation_job=generation_job,
        idempotency_key=payload.idempotencyKey,
        current_user_id=current_user_id,
    )
    db.commit()
    summary = _map_workflow_job_summary(generation_job)
    return {
        "accepted": True,
        "jobId": generation_job.id,
        "jobType": generation_job.job_type,
        "status": summary["status"],
        "phase": summary["phase"],
        "workflowStateUrl": f"/api/products/deck-aistack-codes/decks/{deck_id}/workflow-state",
        "jobUrl": f"/api/workflow-jobs/{generation_job.id}",
    }


def queue_apply_design_version(db: Session, deck_id: str, *, current_user_id: str, payload: WorkflowApplyRequest) -> dict[str, Any]:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        raise ValueError("Deck not found")
    workflow_state = get_deck_workflow_state(db, deck_id)
    current_phase = str((workflow_state or {}).get("phase") or "")
    if current_phase not in {"preview_ready", "applied", "export_ready"}:
        raise WorkflowConflictError(
            code="preview_not_ready",
            message="Generate a preview before applying a design version.",
            recoverable=True,
            next_action="open_preview",
        )
    version = db.query(DesignVersion).filter(DesignVersion.deck_id == deck_id, DesignVersion.id == payload.designVersionId).one_or_none()
    if version is None:
        raise ValueError("Design version not found")

    normalized_input = _normalized_apply_payload(payload)
    existing = get_workflow_job_by_idempotency_key(
        db,
        deck_id=deck_id,
        job_type=JOB_TYPE_APPLY_VERSION,
        idempotency_key=payload.idempotencyKey,
    )
    if existing is not None:
        if _coerce_mapping(existing.input_json) != normalized_input:
            raise WorkflowConflictError(
                code="idempotency_key_conflict",
                message="The idempotency key is already bound to a different apply-design-version request.",
                recoverable=False,
            )
        summary = _map_workflow_job_summary(existing)
        return {
            "accepted": True,
            "jobId": existing.id,
            "jobType": existing.job_type,
            "status": summary["status"],
            "phase": summary["phase"],
            "workflowStateUrl": f"/api/products/deck-aistack-codes/decks/{deck_id}/workflow-state",
            "jobUrl": f"/api/workflow-jobs/{existing.id}",
        }

    apply_job = ensure_workflow_job(
        db,
        deck=deck,
        job_type=JOB_TYPE_APPLY_VERSION,
        status=JOB_STATUS_QUEUED,
        idempotency_key=payload.idempotencyKey,
        max_attempts=1,
        input_payload=normalized_input,
    )
    publisher_job = ensure_workflow_job(
        db,
        deck=deck,
        job_type=JOB_TYPE_DB_PUBLISHER,
        status=JOB_STATUS_QUEUED,
        idempotency_key=f"{payload.idempotencyKey}:publisher",
        max_attempts=1,
        input_payload={
            "publishTarget": "applied",
            "applyWorkflowJobId": apply_job.id,
            "requestedByUserId": current_user_id,
            "designVersionId": payload.designVersionId,
        },
    )
    ensure_workflow_dependency(db, job=publisher_job, depends_on_job=apply_job)
    db.commit()
    summary = _map_workflow_job_summary(apply_job)
    return {
        "accepted": True,
        "jobId": apply_job.id,
        "jobType": apply_job.job_type,
        "status": summary["status"],
        "phase": summary["phase"],
        "workflowStateUrl": f"/api/products/deck-aistack-codes/decks/{deck_id}/workflow-state",
        "jobUrl": f"/api/workflow-jobs/{apply_job.id}",
    }


def queue_export(db: Session, deck_id: str, *, current_user_id: str, payload: WorkflowExportRequest) -> dict[str, Any]:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        raise ValueError("Deck not found")
    workflow_state = get_deck_workflow_state(db, deck_id)
    current_phase = str((workflow_state or {}).get("phase") or "")
    if current_phase not in {"preview_ready", "applied", "export_ready"}:
        raise WorkflowConflictError(
            code="export_not_ready",
            message="Generate or apply a design version before exporting.",
            recoverable=True,
            next_action="open_preview",
        )

    normalized_input = _normalized_export_payload(payload)
    existing = get_workflow_job_by_idempotency_key(
        db,
        deck_id=deck_id,
        job_type=JOB_TYPE_EXPORT,
        idempotency_key=payload.idempotencyKey,
    )
    if existing is not None:
        if _coerce_mapping(existing.input_json) != normalized_input:
            raise WorkflowConflictError(
                code="idempotency_key_conflict",
                message="The idempotency key is already bound to a different export request.",
                recoverable=False,
            )
        publisher_job = ensure_workflow_job(
            db,
            deck=deck,
            job_type=JOB_TYPE_DB_PUBLISHER,
            status=JOB_STATUS_QUEUED,
            idempotency_key=f"{payload.idempotencyKey}:publisher",
            max_attempts=1,
            input_payload={
                "publishTarget": "export_ready",
                "exportWorkflowJobId": existing.id,
                "requestedByUserId": current_user_id,
                "exportType": normalized_input["exportType"],
            },
        )
        ensure_workflow_dependency(db, job=publisher_job, depends_on_job=existing)
        summary = _map_workflow_job_summary(existing)
        return {
            "accepted": True,
            "jobId": existing.id,
            "jobType": existing.job_type,
            "status": summary["status"],
            "phase": summary["phase"],
            "workflowStateUrl": f"/api/products/deck-aistack-codes/decks/{deck_id}/workflow-state",
            "jobUrl": f"/api/workflow-jobs/{existing.id}",
        }

    export_job = ensure_workflow_job(
        db,
        deck=deck,
        job_type=JOB_TYPE_EXPORT,
        status=JOB_STATUS_QUEUED,
        idempotency_key=payload.idempotencyKey,
        max_attempts=1,
        input_payload=normalized_input,
    )
    publisher_job = ensure_workflow_job(
        db,
        deck=deck,
        job_type=JOB_TYPE_DB_PUBLISHER,
        status=JOB_STATUS_QUEUED,
        idempotency_key=f"{payload.idempotencyKey}:publisher",
        max_attempts=1,
        input_payload={
            "publishTarget": "export_ready",
            "exportWorkflowJobId": export_job.id,
            "requestedByUserId": current_user_id,
            "exportType": normalized_input["exportType"],
        },
    )
    ensure_workflow_dependency(db, job=publisher_job, depends_on_job=export_job)
    db.commit()
    summary = _map_workflow_job_summary(export_job)
    return {
        "accepted": True,
        "jobId": export_job.id,
        "jobType": export_job.job_type,
        "status": summary["status"],
        "phase": summary["phase"],
        "workflowStateUrl": f"/api/products/deck-aistack-codes/decks/{deck_id}/workflow-state",
        "jobUrl": f"/api/workflow-jobs/{export_job.id}",
    }


def queue_llm_parallelization(
    db: Session,
    deck_id: str,
    *,
    current_user_id: str,
    payload: WorkflowLlmParallelizationRequest,
) -> dict[str, Any]:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        raise ValueError("Deck not found")

    normalized_input = _normalized_llm_parallelization_payload(payload)
    build_llm_parallelization_batches(
        db,
        deck=deck,
        selected_source_slide_ids=normalized_input["selectedSourceSlideIds"],
        prompt=normalized_input["prompt"],
        partition_count=normalized_input["partitionCount"],
        batch_size=normalized_input["batchSize"],
    )
    existing = get_workflow_job_by_idempotency_key(
        db,
        deck_id=deck_id,
        job_type=JOB_TYPE_LLM_PARALLELIZATION,
        idempotency_key=payload.idempotencyKey,
    )
    if existing is not None:
        if _coerce_mapping(existing.input_json) != normalized_input:
            raise WorkflowConflictError(
                code="idempotency_key_conflict",
                message="The idempotency key is already bound to a different LLM parallelization request.",
                recoverable=False,
            )
        summary = _map_workflow_job_summary(existing)
        return {
            "accepted": True,
            "jobId": existing.id,
            "jobType": existing.job_type,
            "status": summary["status"],
            "phase": summary["phase"],
            "workflowStateUrl": f"/api/products/deck-aistack-codes/decks/{deck_id}/workflow-state",
            "jobUrl": f"/api/workflow-jobs/{existing.id}",
        }

    parallelization_job = ensure_workflow_job(
        db,
        deck=deck,
        job_type=JOB_TYPE_LLM_PARALLELIZATION,
        status=JOB_STATUS_QUEUED,
        idempotency_key=payload.idempotencyKey,
        max_attempts=1,
        input_payload={
            **normalized_input,
            "requestedByUserId": current_user_id,
        },
    )
    db.commit()
    summary = _map_workflow_job_summary(parallelization_job)
    return {
        "accepted": True,
        "jobId": parallelization_job.id,
        "jobType": parallelization_job.job_type,
        "status": summary["status"],
        "phase": summary["phase"],
        "workflowStateUrl": f"/api/products/deck-aistack-codes/decks/{deck_id}/workflow-state",
        "jobUrl": f"/api/workflow-jobs/{parallelization_job.id}",
    }
