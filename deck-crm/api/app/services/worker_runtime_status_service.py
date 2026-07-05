from __future__ import annotations

from datetime import datetime, timedelta
import os

from sqlalchemy.orm import Session

from app.core.security import generate_id
from app.db.models import AgentTelemetryEvent

WORKER_RUN_TYPE = "deck_processing_worker"
WORKER_HEARTBEAT_EVENT = "worker_heartbeat"


def worker_heartbeat_ttl_seconds() -> int:
    return int(os.getenv("DECK_WORKER_HEARTBEAT_TTL_SECONDS", "180"))


def record_worker_heartbeat(
    db: Session,
    *,
    worker_id: str,
    status: str = "alive",
    last_claimed_job_id: str | None = None,
    last_claimed_job_type: str | None = None,
    last_error: str | None = None,
    metadata: dict | None = None,
    commit: bool = True,
) -> dict:
    now = datetime.utcnow()
    event = AgentTelemetryEvent(
        id=generate_id("wkhb"),
        run_type=WORKER_RUN_TYPE,
        event_name=WORKER_HEARTBEAT_EVENT,
        event_level="error" if last_error else "info",
        status=status,
        run_id=last_claimed_job_id,
        error_message_redacted=last_error[:500] if last_error else None,
        metadata_json={
            "workerId": worker_id,
            "lastClaimedJobId": last_claimed_job_id,
            "lastClaimedRunId": last_claimed_job_id,
            "lastClaimedJobType": last_claimed_job_type,
            **(metadata or {}),
        },
        created_at=now,
    )
    db.add(event)
    if commit:
        db.commit()
    return {
        "workerId": worker_id,
        "status": status,
        "lastClaimedJobId": last_claimed_job_id,
        "lastClaimedRunId": last_claimed_job_id,
        "lastClaimedJobType": last_claimed_job_type,
        "lastError": last_error,
        "lastSeenAt": now.isoformat(),
    }


def get_latest_worker_heartbeat(db: Session) -> dict:
    event = (
        db.query(AgentTelemetryEvent)
        .filter(
            AgentTelemetryEvent.run_type == WORKER_RUN_TYPE,
            AgentTelemetryEvent.event_name == WORKER_HEARTBEAT_EVENT,
        )
        .order_by(AgentTelemetryEvent.created_at.desc())
        .first()
    )
    if event is None:
        return {
            "ok": False,
            "status": "missing",
            "message": "No worker heartbeat has been recorded yet.",
            "lastSeenAt": None,
            "workerId": None,
        }

    metadata = event.metadata_json if isinstance(event.metadata_json, dict) else {}
    age_seconds = max(0, int((datetime.utcnow() - event.created_at).total_seconds()))
    stale = event.created_at < datetime.utcnow() - timedelta(seconds=worker_heartbeat_ttl_seconds())
    return {
        "ok": not stale and event.status != "error",
        "status": "stale" if stale else event.status or "unknown",
        "message": "Worker heartbeat is fresh." if not stale else "Worker heartbeat is stale.",
        "lastSeenAt": event.created_at.isoformat(),
        "ageSeconds": age_seconds,
        "ttlSeconds": worker_heartbeat_ttl_seconds(),
        "workerId": metadata.get("workerId"),
        "lastClaimedJobId": metadata.get("lastClaimedJobId") or metadata.get("lastClaimedRunId") or event.run_id,
        "lastClaimedRunId": metadata.get("lastClaimedJobId") or metadata.get("lastClaimedRunId") or event.run_id,
        "lastClaimedJobType": metadata.get("lastClaimedJobType"),
        "lastError": event.error_message_redacted,
    }
