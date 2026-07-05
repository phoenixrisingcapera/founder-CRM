from __future__ import annotations

from datetime import datetime, timedelta
import os
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Deck, WorkflowJob
from app.services.deck_workflow_service import get_deck_workflow_state, queue_source_extraction
from app.services.smart_deck_readiness_service import get_smart_deck_readiness
from app.services.workflow_job_service import JOB_STATUS_RUNNING, JOB_STATUS_QUEUED, set_workflow_job_status


def retry_deck_processing(db: Session, deck_id: str, *, requested_by_user_id: str | None) -> dict[str, Any] | None:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        return None
    readiness_before = get_smart_deck_readiness(db, deck_id)
    accepted = queue_source_extraction(db, deck_id, requested_by_user_id=requested_by_user_id)
    readiness_after = get_smart_deck_readiness(db, deck_id)
    return {
        "deckId": deck_id,
        "action": "retry_processing",
        "changed": True,
        "accepted": accepted,
        "readinessBefore": readiness_before,
        "readinessAfter": readiness_after,
        "message": "Deck processing was requeued through the canonical source pipeline.",
    }


def prepare_smart_deck(db: Session, deck_id: str, *, requested_by_user_id: str | None) -> dict[str, Any] | None:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        return None
    readiness_before = get_smart_deck_readiness(db, deck_id)
    accepted = queue_source_extraction(db, deck_id, requested_by_user_id=requested_by_user_id)
    readiness_after = get_smart_deck_readiness(db, deck_id)
    return {
        "deckId": deck_id,
        "action": "prepare_smart_deck",
        "changed": True,
        "accepted": accepted,
        "readinessBefore": readiness_before,
        "readinessAfter": readiness_after,
        "message": "Smart Deck preparation was requeued through the canonical source pipeline.",
    }


def repair_missing_artifacts(db: Session, deck_id: str, *, requested_by_user_id: str | None) -> dict[str, Any] | None:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        return None
    readiness_before = get_smart_deck_readiness(db, deck_id)
    workflow_before = get_deck_workflow_state(db, deck_id) or {}
    missing_before = list(workflow_before.get("missingArtifacts") or [])
    if not missing_before:
        return {
            "deckId": deck_id,
            "action": "repair_missing_artifacts",
            "changed": False,
            "accepted": None,
            "missingArtifactsBefore": [],
            "missingArtifactsAfter": [],
            "readinessBefore": readiness_before,
            "readinessAfter": readiness_before,
            "message": "No missing workflow artifacts were detected for this deck.",
        }
    accepted = queue_source_extraction(db, deck_id, requested_by_user_id=requested_by_user_id)
    readiness_after = get_smart_deck_readiness(db, deck_id)
    workflow_after = get_deck_workflow_state(db, deck_id) or {}
    return {
        "deckId": deck_id,
        "action": "repair_missing_artifacts",
        "changed": True,
        "accepted": accepted,
        "missingArtifactsBefore": missing_before,
        "missingArtifactsAfter": list(workflow_after.get("missingArtifacts") or []),
        "readinessBefore": readiness_before,
        "readinessAfter": readiness_after,
        "message": "Missing workflow artifacts triggered a source pipeline repair run.",
    }


def requeue_stale_deck_jobs(db: Session, deck_id: str, *, requested_by_user_id: str | None) -> dict[str, Any] | None:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        return None
    readiness_before = get_smart_deck_readiness(db, deck_id)
    stale_after_seconds = int(os.getenv("DECK_WORKER_STALE_AFTER_SECONDS", "900"))
    cutoff = datetime.utcnow() - timedelta(seconds=stale_after_seconds)
    worker_id = f"admin:{requested_by_user_id or 'system'}"
    recovered_job_ids: list[str] = []

    jobs = (
        db.query(WorkflowJob)
        .filter(
            WorkflowJob.deck_id == deck_id,
            WorkflowJob.status == JOB_STATUS_RUNNING,
        )
        .order_by(WorkflowJob.heartbeat_at.asc().nullsfirst(), WorkflowJob.created_at.asc())
        .all()
    )
    for job in jobs:
        heartbeat = job.heartbeat_at or job.updated_at or job.started_at or job.created_at
        lease_expired = job.locked_until is not None and job.locked_until <= datetime.utcnow()
        heartbeat_expired = heartbeat is not None and heartbeat <= cutoff
        if not lease_expired and not heartbeat_expired:
            continue
        output_payload = dict(job.output_json or {})
        output_payload.update(
            {
                "staleRecoveredAt": datetime.utcnow().isoformat(),
                "staleRecoveredBy": worker_id,
                "previousLockedBy": job.locked_by,
                "recoveryReason": "admin_requeue_stale_deck_jobs",
            }
        )
        set_workflow_job_status(
            db,
            job=job,
            status=JOB_STATUS_QUEUED,
            message="Admin requeued stale workflow job for deck recovery.",
            output_payload=output_payload,
        )
        recovered_job_ids.append(job.id)

    if recovered_job_ids:
        db.commit()

    readiness_after = get_smart_deck_readiness(db, deck_id)
    return {
        "deckId": deck_id,
        "action": "requeue_stale_jobs",
        "changed": bool(recovered_job_ids),
        "recoveredJobIds": recovered_job_ids,
        "recoveredJobCount": len(recovered_job_ids),
        "readinessBefore": readiness_before,
        "readinessAfter": readiness_after,
        "message": (
            "Stale workflow jobs were requeued for this deck."
            if recovered_job_ids
            else "No stale running workflow jobs were found for this deck."
        ),
    }
