from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import os
import threading
from typing import Iterator

from sqlalchemy.orm import Session

from app.core.security import generate_id
from app.db.models import CompanyProfile, Deck, DeckExtractionRun, DeckFile, WorkflowJob, WorkflowJobDependency
from app.services.deck_state_machine_service import DeckState, transition_deck_state
from app.services.workflow_job_service import (
    JOB_STATUS_BLOCKED,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED_FINAL,
    JOB_STATUS_FAILED_RETRYABLE,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_TYPE_APPLY_VERSION,
    JOB_TYPE_BRAND_EXTRACTION,
    JOB_TYPE_DB_PUBLISHER,
    JOB_TYPE_EXPORT,
    JOB_TYPE_LLM_GENERATION,
    JOB_TYPE_LLM_PARALLELIZATION,
    JOB_TYPE_MINIATURES,
    JOB_TYPE_PREVIEW_RENDER,
    JOB_TYPE_SCHEMA_VALIDATION,
    JOB_TYPE_SMART_DECK_CONTEXT,
    JOB_TYPE_SOURCE_INGESTION,
    JOB_TYPE_SOURCE_EXTRACTION,
    SOURCE_PIPELINE_JOB_SEQUENCE,
    claim_next_workflow_job,
    fail_pipeline_jobs_from_stage,
    get_workflow_job_by_id,
    recover_stale_workflow_jobs,
    set_workflow_job_status,
    workflow_job_dependencies_status,
    workflow_job_phase,
)

WORKER_KIND_TO_JOB_TYPE = {
    "source_ingestion": JOB_TYPE_SOURCE_INGESTION,
    "source_extraction": JOB_TYPE_SOURCE_EXTRACTION,
    "miniatures": JOB_TYPE_MINIATURES,
    "brand_extraction": JOB_TYPE_BRAND_EXTRACTION,
    "smart_deck_context": JOB_TYPE_SMART_DECK_CONTEXT,
    "db_publisher": JOB_TYPE_DB_PUBLISHER,
    "llm_generation": JOB_TYPE_LLM_GENERATION,
    "llm_parallelization": JOB_TYPE_LLM_PARALLELIZATION,
    "schema_validation": JOB_TYPE_SCHEMA_VALIDATION,
    "preview_render": JOB_TYPE_PREVIEW_RENDER,
    "apply_version": JOB_TYPE_APPLY_VERSION,
    "export": JOB_TYPE_EXPORT,
    "stale_job_rescuer": None,
}

SERVICE_NAME_TO_WORKER_KIND = {
    "worker-source-ingestion": "source_ingestion",
    "worker-source-extraction": "source_extraction",
    "worker-miniatures": "miniatures",
    "worker-brand-extraction": "brand_extraction",
    "worker-smart-deck-context": "smart_deck_context",
    "worker-db-publisher": "db_publisher",
    "worker-llm-generation": "llm_generation",
    "worker-schema-validation": "schema_validation",
    "worker-preview-render": "preview_render",
    "worker-apply-version": "apply_version",
    "worker-export": "export",
    "worker-stale-job-rescuer": "stale_job_rescuer",
    "deck-processing-worker": "stale_job_rescuer",
    "deck-processing-worker-service": "stale_job_rescuer",
}

WORKFLOW_JOB_TYPES = {
    JOB_TYPE_SOURCE_INGESTION,
    JOB_TYPE_SOURCE_EXTRACTION,
    JOB_TYPE_MINIATURES,
    JOB_TYPE_BRAND_EXTRACTION,
    JOB_TYPE_SMART_DECK_CONTEXT,
    JOB_TYPE_DB_PUBLISHER,
    JOB_TYPE_LLM_GENERATION,
    JOB_TYPE_LLM_PARALLELIZATION,
    JOB_TYPE_SCHEMA_VALIDATION,
    JOB_TYPE_PREVIEW_RENDER,
    JOB_TYPE_APPLY_VERSION,
    JOB_TYPE_EXPORT,
}


def _now() -> datetime:
    return datetime.utcnow()


def _heartbeat_interval_seconds() -> float:
    raw_value = str(os.getenv("DECK_WORKER_HEARTBEAT_SECONDS") or "60").strip()
    try:
        parsed = float(raw_value)
    except ValueError:
        return 60.0
    return max(15.0, parsed)


def _truthy_env(name: str) -> bool:
    return str(os.getenv(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def infer_worker_kind_from_service_name(service_name: str | None) -> str | None:
    normalized = str(service_name or "").strip().lower()
    if not normalized:
        return None
    inferred = SERVICE_NAME_TO_WORKER_KIND.get(normalized)
    if inferred:
        return inferred
    if normalized.startswith("worker-"):
        return normalized.removeprefix("worker-").replace("-", "_")
    return None


def worker_kind() -> str | None:
    kind = str(os.getenv("WORKER_KIND") or "").strip().lower().replace("-", "_")
    if kind:
        return kind
    role = str(os.getenv("APP_ROLE") or "").strip().lower().replace("-", "_")
    if role.startswith("worker-"):
        return role.removeprefix("worker-")
    inferred = infer_worker_kind_from_service_name(os.getenv("RAILWAY_SERVICE_NAME"))
    if inferred:
        return inferred
    if role == "worker":
        return None
    return None


def worker_recovery_only() -> bool:
    kind = worker_kind()
    if kind == "stale_job_rescuer":
        return True
    return _truthy_env("DECK_WORKER_RECOVERY_ONLY")


@contextmanager
def _workflow_job_heartbeat(job_id: str, worker_id: str) -> Iterator[None]:
    stop_event = threading.Event()
    interval_seconds = _heartbeat_interval_seconds()

    def _heartbeat_loop() -> None:
        from app.db.session import SessionLocal

        while not stop_event.wait(interval_seconds):
            heartbeat_db = SessionLocal()
            try:
                heartbeat_job = get_workflow_job_by_id(heartbeat_db, job_id)
                if heartbeat_job is None or heartbeat_job.status != JOB_STATUS_RUNNING:
                    heartbeat_db.rollback()
                    return
                set_workflow_job_status(
                    heartbeat_db,
                    job=heartbeat_job,
                    status=heartbeat_job.status,
                    worker_id=worker_id,
                    heartbeat_only=True,
                )
                heartbeat_db.commit()
            except Exception:
                heartbeat_db.rollback()
                return
            finally:
                heartbeat_db.close()

    thread = threading.Thread(
        target=_heartbeat_loop,
        name=f"workflow-heartbeat-{job_id}",
        daemon=True,
    )
    thread.start()
    try:
        yield
    finally:
        stop_event.set()
        thread.join(timeout=min(interval_seconds, 5.0))


def configured_worker_job_types() -> set[str]:
    kind = worker_kind()
    configured: set[str] = set()
    if kind:
        mapped = WORKER_KIND_TO_JOB_TYPE.get(kind)
        if mapped is None and kind != "stale_job_rescuer":
            raise RuntimeError(f"Unsupported worker kind: {kind}")
        if mapped is not None:
            configured.add(mapped)
    legacy_configured = {
        value.strip()
        for value in str(os.getenv("DECK_WORKER_JOB_TYPES") or "").split(",")
        if value.strip()
    }
    if legacy_configured:
        configured |= legacy_configured
    unknown = configured - WORKFLOW_JOB_TYPES
    if unknown:
        raise RuntimeError(f"Unsupported workflow job types: {', '.join(sorted(unknown))}")
    if worker_recovery_only():
        return configured or set(WORKFLOW_JOB_TYPES)
    if not configured:
        if _truthy_env("DECK_WORKER_ALLOW_ALL_JOB_TYPES"):
            return set(WORKFLOW_JOB_TYPES)
        raise RuntimeError(
            "DECK_WORKER_JOB_TYPES must be configured for non-recovery workers. "
            "Production workers should claim a dedicated job_type."
        )
    if len(configured) > 1 and not _truthy_env("DECK_WORKER_ALLOW_MULTI_JOB_TYPES"):
        raise RuntimeError(
            "Production workers should claim exactly one workflow job_type. "
            "Set DECK_WORKER_ALLOW_MULTI_JOB_TYPES=true only for an explicit break-glass worker."
        )
    return configured


def _configured_job_types() -> set[str]:
    return configured_worker_job_types()


def _job_payload(job: WorkflowJob) -> dict:
    return dict(job.input_json or {})


def _job_output(job: WorkflowJob) -> dict:
    return dict(job.output_json or {})


def _dependency_jobs(db: Session, job: WorkflowJob) -> list[WorkflowJob]:
    dependencies = (
        db.query(WorkflowJobDependency)
        .filter(WorkflowJobDependency.job_id == job.id)
        .order_by(WorkflowJobDependency.created_at.asc())
        .all()
    )
    jobs: list[WorkflowJob] = []
    for dependency in dependencies:
        upstream = db.query(WorkflowJob).filter(WorkflowJob.id == dependency.depends_on_job_id).one_or_none()
        if upstream is not None:
            jobs.append(upstream)
    return jobs


def _dependency_output(db: Session, job: WorkflowJob, job_type: str) -> dict:
    for dependency_job in _dependency_jobs(db, job):
        if dependency_job.job_type == job_type:
            return _job_output(dependency_job)
    return {}


def _processing_run(job: WorkflowJob, db: Session) -> DeckExtractionRun | None:
    if job.extraction_run_id:
        run = db.query(DeckExtractionRun).filter(DeckExtractionRun.id == job.extraction_run_id).one_or_none()
        if run is not None:
            return run

    if job.job_type not in {
        JOB_TYPE_SOURCE_EXTRACTION,
        JOB_TYPE_MINIATURES,
        JOB_TYPE_BRAND_EXTRACTION,
        JOB_TYPE_SMART_DECK_CONTEXT,
        JOB_TYPE_DB_PUBLISHER,
    }:
        return None

    deck = db.query(Deck).filter(Deck.id == job.deck_id).one_or_none()
    if deck is None:
        return None
    deck_file = (
        db.query(DeckFile)
        .filter(DeckFile.deck_id == deck.id)
        .order_by(DeckFile.uploaded_at.desc(), DeckFile.created_at.desc())
        .first()
    )
    source_file_id = deck_file.id if deck_file is not None else None

    run = DeckExtractionRun(
        id=generate_id("process"),
        deck_id=deck.id,
        source_file_id=source_file_id,
        run_type="deck_processing_queue",
        extractor_name="workflow_source_pipeline",
        extractor_version="v2",
        source_format=deck_file.file_extension if deck_file is not None else None,
        status="queued",
        metadata_json={
            "stage": "workflow_compatibility_created",
            "stageLabel": "Workflow compatibility created",
            "nextAction": "wait_for_worker",
            "workflowJobId": job.id,
            "workflowJobType": job.job_type,
        },
    )
    db.add(run)
    db.flush()
    job.extraction_run_id = run.id
    return run


def _deck(job: WorkflowJob, db: Session) -> Deck:
    deck = db.query(Deck).filter(Deck.id == job.deck_id).one_or_none()
    if deck is None:
        raise ValueError("Deck not found")
    return deck


def _failure_status_for_job(job: WorkflowJob) -> str:
    return JOB_STATUS_FAILED_FINAL if int(job.attempt_count or 0) >= int(job.max_attempts or 1) else JOB_STATUS_FAILED_RETRYABLE


def _mark_run_stage(run: DeckExtractionRun, *, stage: str, next_action: str, worker_id: str, extra: dict | None = None) -> None:
    metadata = dict(run.metadata_json or {})
    metadata.update(
        {
            "stage": stage,
            "stageLabel": stage.replace("_", " ").title(),
            "nextAction": next_action,
            "lockedBy": worker_id,
            "workerId": worker_id,
            "heartbeatAt": _now().isoformat(),
        }
    )
    if extra:
        metadata.update(extra)
    run.metadata_json = metadata


def _source_pipeline_jobs(db: Session, run: DeckExtractionRun) -> dict[str, WorkflowJob]:
    jobs = {
        job.job_type: job
        for job in db.query(WorkflowJob)
        .filter(WorkflowJob.extraction_run_id == run.id, WorkflowJob.job_type.in_(SOURCE_PIPELINE_JOB_SEQUENCE[1:]))
        .all()
    }
    return jobs


def _mark_source_pipeline_failed(
    db: Session,
    *,
    run: DeckExtractionRun,
    first_failed_job_type: str,
    worker_id: str,
    error_code: str,
    error_message: str,
) -> None:
    jobs = _source_pipeline_jobs(db, run)
    if jobs:
        fail_pipeline_jobs_from_stage(
            db,
            jobs=jobs,
            first_failed_job_type=first_failed_job_type,
            worker_id=worker_id,
            error_code=error_code,
            error_message=error_message,
        )


def _ensure_company_profile(db: Session, deck: Deck) -> CompanyProfile:
    profile = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.workspace_id == deck.workspace_id)
        .order_by(CompanyProfile.updated_at.desc(), CompanyProfile.created_at.desc())
        .first()
    )
    if profile is not None:
        return profile

    profile = CompanyProfile(
        id=generate_id("company"),
        workspace_id=deck.workspace_id,
        canonical_name=deck.title or "Deck company",
        website_url=None,
        contact_email=None,
        inferred_stage=None,
        founder_name=None,
        team_summary=None,
        linkedin_urls_json=None,
        source_notes_json=None,
    )
    db.add(profile)
    db.flush()
    return profile


def process_workflow_job(db: Session, job_id: str, *, worker_id: str) -> dict:
    job = get_workflow_job_by_id(db, job_id)
    if job is None:
        raise ValueError("Workflow job not found")

    from app.workers.job_handlers import get_workflow_job_handler

    handler = get_workflow_job_handler(job.job_type)
    if handler is None:
        raise ValueError(f"Unsupported workflow job type: {job.job_type}")

    try:
        with _workflow_job_heartbeat(job.id, worker_id):
            handler(db, job, worker_id=worker_id)
    except Exception as exc:
        db.rollback()
        refreshed = get_workflow_job_by_id(db, job_id)
        if refreshed is not None and refreshed.status == JOB_STATUS_RUNNING:
            failure_status = _failure_status_for_job(refreshed)
            set_workflow_job_status(
                db,
                job=refreshed,
                status=failure_status,
                worker_id=worker_id,
                message=str(exc),
                error_code=f"{refreshed.job_type}_failed",
                error_message=str(exc),
                output_payload={"phase": "failed_final" if failure_status == JOB_STATUS_FAILED_FINAL else "failed_retryable"},
            )
            if refreshed.job_type == JOB_TYPE_DB_PUBLISHER and failure_status == JOB_STATUS_FAILED_FINAL:
                deck = db.query(Deck).filter(Deck.id == refreshed.deck_id).one_or_none()
                if deck is not None:
                    transition_deck_state(
                        db,
                        deck,
                        DeckState.FAILED,
                        reason="workflow_db_publisher_failed",
                        summary=f"Workflow publisher failed: {exc}",
                        source_surface="workflow_db_publisher",
                        source_route=f"/decks/{deck.id}/workflow",
                        metadata={"workflowJobId": refreshed.id, "workerId": worker_id},
                    )
            db.commit()
        raise

    refreshed = get_workflow_job_by_id(db, job_id)
    if refreshed is None:
        raise ValueError("Workflow job disappeared after processing.")
    return {
        "id": refreshed.id,
        "deckId": refreshed.deck_id,
        "jobType": refreshed.job_type,
        "status": refreshed.status,
        "phase": workflow_job_phase(refreshed.job_type, refreshed.status, output_payload=_job_output(refreshed)),
    }


def recover_stale_processing_runs(db: Session, *, worker_id: str) -> dict:
    return recover_stale_workflow_jobs(
        db,
        worker_id=worker_id,
        job_types=_configured_job_types(),
        stale_after_seconds=int(os.getenv("DECK_WORKER_STALE_AFTER_SECONDS", "900")),
        recovery_limit=int(os.getenv("DECK_WORKER_STALE_RECOVERY_LIMIT", "25")),
    )


def process_next_durable_deck(db: Session, *, worker_id: str) -> dict | None:
    job = claim_next_workflow_job(db, worker_id=worker_id, job_types=_configured_job_types())
    if job is None:
        return None
    return process_workflow_job(db, job.id, worker_id=worker_id)
