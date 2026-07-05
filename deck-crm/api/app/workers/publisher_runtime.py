from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import WorkflowJob
from app.services.deck_processing_worker_service import _deck, _job_payload, _mark_run_stage, _now, _processing_run
from app.services.deck_state_machine_service import DeckState, transition_deck_state
from app.services.export_service import create_export
from app.services.workflow_job_service import (
    JOB_STATUS_COMPLETED,
    PUBLISHABLE_WORKFLOW_PHASES,
    record_workflow_artifact,
    set_workflow_job_status,
)


def handle_db_publisher(db: Session, job: WorkflowJob, *, worker_id: str) -> None:
    deck = _deck(job, db)
    payload = _job_payload(job)
    target = str(payload.get("publishTarget") or "smart_deck_ready")
    run = _processing_run(job, db)

    if target not in PUBLISHABLE_WORKFLOW_PHASES:
        raise ValueError(f"Unsupported db_publisher target: {target}")

    if target == "smart_deck_ready":
        transition_deck_state(
            db,
            deck,
            DeckState.READY,
            reason="workflow_db_publisher_smart_deck_ready",
            summary="Smart Deck source pipeline completed and was published by the workflow orchestrator.",
            source_surface="workflow_db_publisher",
            source_route=f"/decks/{deck.id}/workflow",
            metadata={"workflowJobId": job.id, "workerId": worker_id},
        )
        if run is not None:
            run.status = "completed"
            run.completed_at = run.completed_at or _now()
            _mark_run_stage(run, stage="smart_deck_context_ready", next_action="open_smart_deck", worker_id=worker_id)
        output_payload = {
            "phase": "smart_deck_ready",
            "deckState": DeckState.READY.value,
            "publishedAt": _now().isoformat(),
        }
    elif target == "preview_ready":
        transition_deck_state(
            db,
            deck,
            DeckState.READY,
            reason="workflow_db_publisher_preview_ready",
            summary="Smart Deck preview was published by the workflow orchestrator.",
            source_surface="workflow_db_publisher",
            source_route=f"/decks/{deck.id}/workflow",
            metadata={"workflowJobId": job.id, "workerId": worker_id, "publishTarget": target},
        )
        output_payload = {
            "phase": "preview_ready",
            "deckState": DeckState.READY.value,
            "publishedAt": _now().isoformat(),
        }
    elif target == "applied":
        transition_deck_state(
            db,
            deck,
            DeckState.READY,
            reason="workflow_db_publisher_applied",
            summary="Applied design version was published by the workflow orchestrator.",
            source_surface="workflow_db_publisher",
            source_route=f"/decks/{deck.id}/workflow",
            metadata={"workflowJobId": job.id, "workerId": worker_id, "publishTarget": target},
        )
        output_payload = {
            "phase": "applied",
            "deckState": DeckState.READY.value,
            "publishedAt": _now().isoformat(),
        }
    elif target == "export_ready":
        transition_deck_state(
            db,
            deck,
            DeckState.READY,
            reason="workflow_db_publisher_export_ready",
            summary="Deck export was published by the workflow orchestrator.",
            source_surface="workflow_db_publisher",
            source_route=f"/decks/{deck.id}/workflow",
            metadata={"workflowJobId": job.id, "workerId": worker_id, "publishTarget": target},
        )
        output_payload = {
            "phase": "export_ready",
            "deckState": DeckState.READY.value,
            "publishedAt": _now().isoformat(),
        }
    else:
        deck.summary = "Workflow publisher completed."
        output_payload = {
            "phase": target,
            "deckState": deck.status,
            "publishedAt": _now().isoformat(),
        }

    set_workflow_job_status(
        db,
        job=job,
        status=JOB_STATUS_COMPLETED,
        worker_id=worker_id,
        message=f"Publisher marked {target}.",
        output_payload=output_payload,
        published_phase=target,
    )
    db.commit()


def handle_export(db: Session, job: WorkflowJob, *, worker_id: str) -> None:
    payload = _job_payload(job)
    export_type = str(payload.get("exportType") or "").strip()
    if not export_type:
        raise ValueError("Workflow export job is missing exportType.")
    export_payload = create_export(db, job.deck_id, export_type)
    if export_payload is None:
        raise ValueError("Export could not be created.")
    export_id = str(export_payload.get("id") or "").strip()
    storage_key = export_payload.get("downloadUrl") or export_payload.get("download_url") or f"/api/decks/{job.deck_id}/exports/{export_id}/download"
    record_workflow_artifact(
        db,
        job=job,
        artifact_type="deck_export",
        storage_key=storage_key,
        metadata={
            "exportId": export_id,
            "exportType": export_type,
            "downloadUrl": export_payload.get("downloadUrl") or export_payload.get("download_url"),
        },
    )
    set_workflow_job_status(
        db,
        job=job,
        status=JOB_STATUS_COMPLETED,
        worker_id=worker_id,
        message="Export stage completed.",
        output_payload={
            "phase": "export_ready",
            "exportId": export_id,
            "exportType": export_type,
            "downloadUrl": export_payload.get("downloadUrl") or export_payload.get("download_url"),
        },
    )
    db.commit()
