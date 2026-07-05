from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import DeckBrandAsset, DeckInputSource, WorkflowJob
from app.services.brand_enrichment_service import enrich_brand_profile_after_extract
from app.services.brand_loader_service import upsert_brand_profile
from app.services.deck_processing_worker_service import (
    _deck,
    _ensure_company_profile,
    _failure_status_for_job,
    _job_payload,
    _mark_run_stage,
    _mark_source_pipeline_failed,
    _now,
    _processing_run,
)
from app.services.deck_structure_service import extract_and_persist_deck_structure
from app.services.presentation_miniature_service import extract_presentation_miniatures
from app.services.smart_deck_job_service import prepare_smart_deck_source_workspace
from app.services.workflow_job_service import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED_FINAL,
    JOB_TYPE_BRAND_EXTRACTION,
    JOB_TYPE_MINIATURES,
    JOB_TYPE_SMART_DECK_CONTEXT,
    JOB_TYPE_SOURCE_EXTRACTION,
    set_workflow_job_status,
)


def handle_source_ingestion(db: Session, job: WorkflowJob, *, worker_id: str) -> None:
    deck = _deck(job, db)
    payload = _job_payload(job)
    output_payload = {
        "phase": "source_file_saved",
        "deckFileId": payload.get("deckFileId"),
        "sourceInputId": payload.get("sourceInputId"),
        "storagePath": payload.get("storagePath"),
        "ingestionMode": payload.get("ingestionMode"),
    }
    set_workflow_job_status(
        db,
        job=job,
        status=JOB_STATUS_COMPLETED,
        worker_id=worker_id,
        message=f"Source ingestion confirmed for deck {deck.id}.",
        output_payload=output_payload,
    )
    db.commit()


def handle_source_extraction(db: Session, job: WorkflowJob, *, worker_id: str) -> None:
    run = _processing_run(job, db)
    if run is None:
        raise ValueError("Workflow source extraction job is missing its extraction run.")
    deck = _deck(job, db)
    run.status = "running"
    run.started_at = run.started_at or _now()
    _mark_run_stage(run, stage="structure_extraction_running", next_action="wait_for_source_extraction", worker_id=worker_id)
    db.commit()

    try:
        structure = extract_and_persist_deck_structure(db, deck.id, publish_ready_state=False)
        refreshed_run = _processing_run(job, db)
        if refreshed_run is None:
            raise ValueError("Extraction run disappeared after source extraction.")
        source_workspace = dict((refreshed_run.metrics_json or {}).get("sourceWorkspace") or {})
        source_enrichment = dict((refreshed_run.metrics_json or {}).get("sourceEnrichment") or {})
        _mark_run_stage(
            refreshed_run,
            stage="source_extraction_completed",
            next_action="wait_for_miniatures",
            worker_id=worker_id,
            extra={
                "slideCount": refreshed_run.slide_count,
                "blockCount": refreshed_run.block_count,
                "assetCount": refreshed_run.asset_count,
            },
        )
        set_workflow_job_status(
            db,
            job=job,
            status=JOB_STATUS_COMPLETED,
            worker_id=worker_id,
            message="Source extraction completed.",
            output_payload={
                "phase": "source_ready",
                "slideCount": refreshed_run.slide_count,
                "blockCount": refreshed_run.block_count,
                "assetCount": refreshed_run.asset_count,
                "sourceWorkspace": source_workspace,
                "sourceEnrichment": source_enrichment,
                "processingMode": "structured_extraction",
                "structureStatus": structure.get("status"),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        failure_status = _failure_status_for_job(job)
        failed_run = _processing_run(job, db)
        if failed_run is not None:
            failed_run.status = "failed"
            failed_run.error_message = str(exc)
            failed_run.completed_at = _now()
            _mark_run_stage(
                failed_run,
                stage="failed",
                next_action="manual_review",
                worker_id=worker_id,
                extra={"failureCode": "source_extraction_failed"},
            )
            if failure_status == JOB_STATUS_FAILED_FINAL:
                _mark_source_pipeline_failed(
                    db,
                    run=failed_run,
                    first_failed_job_type=JOB_TYPE_SOURCE_EXTRACTION,
                    worker_id=worker_id,
                    error_code="source_extraction_failed",
                    error_message=str(exc),
                )
        set_workflow_job_status(
            db,
            job=job,
            status=failure_status,
            worker_id=worker_id,
            message="Source extraction failed.",
            error_code="source_extraction_failed",
            error_message=str(exc),
            output_payload={"phase": "failed_final" if failure_status == JOB_STATUS_FAILED_FINAL else "failed_retryable"},
        )
        db.commit()
        raise


def handle_miniatures(db: Session, job: WorkflowJob, *, worker_id: str) -> None:
    run = _processing_run(job, db)
    if run is None:
        raise ValueError("Workflow miniatures job is missing its extraction run.")
    _mark_run_stage(run, stage="preview_generation_running", next_action="wait_for_preview_generation", worker_id=worker_id)
    db.commit()

    try:
        preview = extract_presentation_miniatures(db, job.deck_id, publish_ready_state=False)
        refreshed_run = _processing_run(job, db)
        if refreshed_run is not None:
            _mark_run_stage(
                refreshed_run,
                stage="preview_generation_completed",
                next_action="wait_for_smart_deck_context",
                worker_id=worker_id,
                extra={"previewCount": int(preview.get("previewCount") or preview.get("slideCount") or 0)},
            )
        set_workflow_job_status(
            db,
            job=job,
            status=JOB_STATUS_COMPLETED,
            worker_id=worker_id,
            message="Miniatures completed.",
            output_payload={
                "phase": "source_ready",
                "slideCount": int(preview.get("slideCount") or 0),
                "previewCount": int(preview.get("previewCount") or preview.get("slideCount") or 0),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        failure_status = _failure_status_for_job(job)
        failed_run = _processing_run(job, db)
        if failed_run is not None and failure_status == JOB_STATUS_FAILED_FINAL:
            _mark_source_pipeline_failed(
                db,
                run=failed_run,
                first_failed_job_type=JOB_TYPE_MINIATURES,
                worker_id=worker_id,
                error_code="thumbnail_generation_failed",
                error_message=str(exc),
            )
        set_workflow_job_status(
            db,
            job=job,
            status=failure_status,
            worker_id=worker_id,
            message="Miniatures generation failed.",
            error_code="thumbnail_generation_failed",
            error_message=str(exc),
            output_payload={"phase": "failed_final" if failure_status == JOB_STATUS_FAILED_FINAL else "failed_retryable"},
        )
        db.commit()
        raise


def handle_brand_extraction(db: Session, job: WorkflowJob, *, worker_id: str) -> None:
    deck = _deck(job, db)
    run = _processing_run(job, db)
    if run is not None:
        _mark_run_stage(run, stage="brand_extraction_running", next_action="wait_for_brand_extraction", worker_id=worker_id)
    db.commit()

    try:
        company_profile = _ensure_company_profile(db, deck)
        input_sources = db.query(DeckInputSource).filter(DeckInputSource.deck_id == deck.id).order_by(DeckInputSource.created_at.asc()).all()
        brand_assets = db.query(DeckBrandAsset).filter(DeckBrandAsset.deck_id == deck.id).order_by(DeckBrandAsset.created_at.asc()).all()
        profile = upsert_brand_profile(
            db,
            deck,
            company_profile,
            input_sources,
            brand_assets,
            deck.audience or "general audience",
            deck.purpose or "smart deck generation",
        )
        db.commit()
        enrich_brand_profile_after_extract(db, deck.id)
        db.refresh(profile)
        if run is not None:
            _mark_run_stage(run, stage="brand_extraction_completed", next_action="brand_profile_ready", worker_id=worker_id)
        set_workflow_job_status(
            db,
            job=job,
            status=JOB_STATUS_COMPLETED,
            worker_id=worker_id,
            message="Brand extraction completed.",
            output_payload={
                "phase": "source_ready",
                "brandProfileId": profile.id,
                "processingStatus": profile.processing_status,
                "palette": profile.palette_json or [],
                "logoUrl": profile.logo_url,
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        failure_status = _failure_status_for_job(job)
        if run is not None and failure_status == JOB_STATUS_FAILED_FINAL:
            _mark_source_pipeline_failed(
                db,
                run=run,
                first_failed_job_type=JOB_TYPE_BRAND_EXTRACTION,
                worker_id=worker_id,
                error_code="brand_extraction_failed",
                error_message=str(exc),
            )
        set_workflow_job_status(
            db,
            job=job,
            status=failure_status,
            worker_id=worker_id,
            message="Brand extraction failed.",
            error_code="brand_extraction_failed",
            error_message=str(exc),
            output_payload={"phase": "failed_final" if failure_status == JOB_STATUS_FAILED_FINAL else "failed_retryable"},
        )
        db.commit()
        raise


def handle_smart_deck_context(db: Session, job: WorkflowJob, *, worker_id: str) -> None:
    run = _processing_run(job, db)
    if run is not None:
        _mark_run_stage(run, stage="smart_deck_context_running", next_action="wait_for_smart_deck_context", worker_id=worker_id)
    db.commit()

    try:
        workspace = prepare_smart_deck_source_workspace(db, job.deck_id, commit=False, publish_ready_state=False)
        refreshed_run = _processing_run(job, db)
        if refreshed_run is not None:
            _mark_run_stage(
                refreshed_run,
                stage="smart_deck_context_completed",
                next_action="wait_for_publisher",
                worker_id=worker_id,
                extra={"workspaceId": workspace.get("workspaceId")},
            )
        set_workflow_job_status(
            db,
            job=job,
            status=JOB_STATUS_COMPLETED,
            worker_id=worker_id,
            message="Smart Deck context completed.",
            output_payload={
                "phase": "source_ready",
                "workspaceId": workspace.get("workspaceId"),
                "sourceRunId": workspace.get("sourceRunId"),
                "slideCount": workspace.get("slideCount"),
                "artifactCount": workspace.get("artifactCount"),
                "enrichmentSource": workspace.get("enrichmentSource"),
                "llmStatus": workspace.get("llmStatus"),
                "llmProvider": workspace.get("llmProvider"),
                "llmModel": workspace.get("llmModel"),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        failure_status = _failure_status_for_job(job)
        failed_run = _processing_run(job, db)
        if failed_run is not None and failure_status == JOB_STATUS_FAILED_FINAL:
            _mark_source_pipeline_failed(
                db,
                run=failed_run,
                first_failed_job_type=JOB_TYPE_SMART_DECK_CONTEXT,
                worker_id=worker_id,
                error_code="smart_deck_context_failed",
                error_message=str(exc),
            )
        set_workflow_job_status(
            db,
            job=job,
            status=failure_status,
            worker_id=worker_id,
            message="Smart Deck context failed.",
            error_code="smart_deck_context_failed",
            error_message=str(exc),
            output_payload={"phase": "failed_final" if failure_status == JOB_STATUS_FAILED_FINAL else "failed_retryable"},
        )
        db.commit()
        raise
