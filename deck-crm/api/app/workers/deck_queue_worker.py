from __future__ import annotations

import logging
import os
import signal
import socket
import time

from app.core.railway_env import apply_railway_env_aliases


apply_railway_env_aliases()

from app.db.session import SessionLocal
from app.services.deck_processing_worker_service import (
    configured_worker_job_types,
    process_next_durable_deck,
    recover_stale_processing_runs,
    worker_kind,
    worker_recovery_only,
)
from app.services.worker_runtime_status_service import record_worker_heartbeat

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("deck_queue_worker")

POLL_INTERVAL_SECONDS = int(os.getenv("DECK_WORKER_POLL_INTERVAL_SECONDS", "10"))
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("DECK_WORKER_HEARTBEAT_INTERVAL_SECONDS", "30"))
WORKER_ID = os.getenv("DECK_WORKER_ID") or f"{socket.gethostname()}:{os.getpid()}"
STOP_REQUESTED = False
LAST_HEARTBEAT_AT = 0.0
LAST_CLAIMED_JOB_ID: str | None = None
LAST_CLAIMED_JOB_TYPE: str | None = None


def _configured_job_types_csv() -> str:
    return ",".join(sorted(configured_worker_job_types()))


def _worker_kind_label() -> str:
    return worker_kind() or "worker"


def _request_stop(signum, frame) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True
    logger.info("deck_worker_stop_requested", extra={"signal": signum, "worker_id": WORKER_ID})


def _record_heartbeat(*, force: bool = False, status: str = "alive", last_error: str | None = None) -> None:
    global LAST_HEARTBEAT_AT
    now = time.monotonic()
    if not force and now - LAST_HEARTBEAT_AT < HEARTBEAT_INTERVAL_SECONDS:
        return
    db = SessionLocal()
    try:
        record_worker_heartbeat(
            db,
            worker_id=WORKER_ID,
            status=status,
            last_claimed_job_id=LAST_CLAIMED_JOB_ID,
            last_claimed_job_type=LAST_CLAIMED_JOB_TYPE,
            last_error=last_error,
            metadata={
                "pollIntervalSeconds": POLL_INTERVAL_SECONDS,
                "configuredJobTypes": _configured_job_types_csv(),
                "workerKind": _worker_kind_label(),
            },
            commit=True,
        )
        LAST_HEARTBEAT_AT = now
    except Exception:
        logger.exception("deck_worker_heartbeat_failed", extra={"worker_id": WORKER_ID})
    finally:
        db.close()


def _recover_stale_runs() -> dict:
    db = SessionLocal()
    try:
        return recover_stale_processing_runs(db, worker_id=WORKER_ID)
    except Exception:
        logger.exception("deck_worker_stale_recovery_failed", extra={"worker_id": WORKER_ID})
        return {"recovered": 0, "timedOut": 0}
    finally:
        db.close()


def run_once() -> bool:
    global LAST_CLAIMED_JOB_ID, LAST_CLAIMED_JOB_TYPE
    if worker_recovery_only():
        recovery = _recover_stale_runs()
        _record_heartbeat(force=True, status="alive")
        logger.info(
            "deck_worker_recovered_stale_jobs",
            extra={
                "worker_id": WORKER_ID,
                "recovered": recovery.get("recovered", 0),
                "timed_out": recovery.get("timedOut", 0),
            },
        )
        return False

    db = SessionLocal()
    try:
        result = process_next_durable_deck(db, worker_id=WORKER_ID)
        if result is None:
            _record_heartbeat()
            return False

        LAST_CLAIMED_JOB_ID = str(result.get("id") or "") or LAST_CLAIMED_JOB_ID
        LAST_CLAIMED_JOB_TYPE = str(result.get("jobType") or "") or LAST_CLAIMED_JOB_TYPE
        _record_heartbeat(force=True)
        logger.info(
            "deck_worker_processed_job",
            extra={
                "workflow_job_id": result.get("id"),
                "deck_id": result.get("deckId"),
                "job_type": result.get("jobType"),
                "status": result.get("status"),
                "phase": result.get("phase"),
                "worker_id": WORKER_ID,
            },
        )
        return True
    except Exception as exc:
        _record_heartbeat(force=True, status="error", last_error=str(exc))
        logger.exception("deck_worker_job_failed", extra={"worker_id": WORKER_ID})
        return False
    finally:
        db.close()


def main() -> None:
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    logger.info(
        "deck_worker_started",
        extra={
            "poll_interval_seconds": POLL_INTERVAL_SECONDS,
            "worker_id": WORKER_ID,
            "configured_job_types": _configured_job_types_csv(),
            "recovery_only": worker_recovery_only(),
        },
    )

    _record_heartbeat(force=True, status="started")

    while not STOP_REQUESTED:
        processed = run_once()
        if not processed:
            time.sleep(POLL_INTERVAL_SECONDS)

    _record_heartbeat(force=True, status="stopped")
    logger.info("deck_worker_stopped", extra={"worker_id": WORKER_ID})


if __name__ == "__main__":
    main()
