from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)


def _apply_storage_env_aliases() -> None:
    aliases = {
        "BUCKET": "RAILWAY_BUCKET_NAME",
        "REGION": "RAILWAY_BUCKET_REGION",
        "ENDPOINT": "RAILWAY_BUCKET_ENDPOINT",
        "ACCESS_" + "KEY_ID": "RAILWAY_BUCKET_" + "ACCESS_KEY",
        "SECRET_" + "ACCESS_KEY": "RAILWAY_BUCKET_" + "SECRET_KEY",
    }
    for source, target in aliases.items():
        value = os.getenv(source)
        if value and not os.getenv(target):
            os.environ[target] = value


_apply_storage_env_aliases()
os.environ.setdefault("UPLOAD_SECURITY_SCAN_COMMAND", "disabled")

from app.db.session import SessionLocal
from app.services.deck_processing_worker_service import (
    configured_worker_job_types,
    infer_worker_kind_from_service_name,
    process_next_durable_deck,
    recover_stale_processing_runs,
    worker_recovery_only,
)
from app.services.worker_runtime_status_service import record_worker_heartbeat

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("deck_processing_worker")

DEFAULT_IDLE_SLEEP_SECONDS = float(os.getenv("DECK_WORKER_POLL_INTERVAL_SECONDS", "10"))
HEARTBEAT_INTERVAL_SECONDS = float(os.getenv("DECK_WORKER_HEARTBEAT_INTERVAL_SECONDS", "30"))
WORKER_ID = os.getenv("DECK_WORKER_ID") or f"{socket.gethostname()}:{os.getpid()}"
LAST_HEARTBEAT_AT = 0.0
LAST_CLAIMED_RUN_ID: str | None = None
LAST_STATUS = "starting"
LAST_ERROR: str | None = None


class _WorkerHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in {"/api/health", "/health"}:
            self.send_response(404)
            self.end_headers()
            return
        role = os.getenv("APP_ROLE", "worker")
        kind = os.getenv("WORKER_KIND", "")
        job_types = os.getenv("DECK_WORKER_JOB_TYPES", "")
        body = json.dumps(
            {
                "status": "ok",
                "role": role,
                "kind": kind,
                "jobTypes": job_types,
                "workerId": WORKER_ID,
                "workerStatus": LAST_STATUS,
                "lastClaimedRunId": LAST_CLAIMED_RUN_ID,
                "lastError": LAST_ERROR,
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def _record_heartbeat(
    *,
    force: bool = False,
    status: str = "alive",
    last_error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    global LAST_HEARTBEAT_AT, LAST_STATUS, LAST_ERROR
    LAST_STATUS = status
    LAST_ERROR = last_error
    now = time.monotonic()
    if not force and now - LAST_HEARTBEAT_AT < HEARTBEAT_INTERVAL_SECONDS:
        return

    db = SessionLocal()
    try:
        record_worker_heartbeat(
            db,
            worker_id=WORKER_ID,
            status=status,
            last_claimed_run_id=LAST_CLAIMED_RUN_ID,
            last_error=last_error,
            metadata={
                "pollIntervalSeconds": DEFAULT_IDLE_SLEEP_SECONDS,
                "entrypoint": "scripts/deck_processing_worker.py",
                **(metadata or {}),
            },
            commit=True,
        )
        LAST_HEARTBEAT_AT = now
    except Exception:
        logger.exception("deck_worker_heartbeat_failed", extra={"worker_id": WORKER_ID})
    finally:
        db.close()


def _recover_stale_runs() -> dict[str, Any]:
    db = SessionLocal()
    try:
        return recover_stale_processing_runs(db, worker_id=WORKER_ID)
    except Exception:
        logger.exception("deck_worker_stale_recovery_failed", extra={"worker_id": WORKER_ID})
        return {"recovered": 0, "finalFailed": 0}
    finally:
        db.close()


def run_once(*, configured_job_types: str | None = None, recovery_only: bool = False) -> bool:
    global LAST_CLAIMED_RUN_ID

    if recovery_only:
        recovery = _recover_stale_runs()
        _record_heartbeat(
            force=True,
            status="recovery",
            metadata={
                "configuredJobTypes": configured_job_types,
                "recoveryOnly": True,
                "recovered": recovery.get("recovered", 0),
                "timedOut": recovery.get("timedOut", 0),
            },
        )
        logger.info(
            "deck_worker_stale_recovery_cycle",
            extra={"worker_id": WORKER_ID, **recovery},
        )
        return False

    db = SessionLocal()
    try:
        result = process_next_durable_deck(db, worker_id=WORKER_ID)
        if result is None:
            _record_heartbeat(
                status="idle",
                metadata={"configuredJobTypes": configured_job_types},
            )
            return False

        LAST_CLAIMED_RUN_ID = str(result.get("id") or "") or LAST_CLAIMED_RUN_ID
        _record_heartbeat(
            force=True,
            status="processed",
            metadata={"configuredJobTypes": configured_job_types},
        )
        logger.info(
            "deck_worker_processed_job",
            extra={
                "processing_run_id": result.get("id"),
                "deck_id": result.get("deckId"),
                "status": result.get("status"),
                "stage": result.get("stage"),
                "worker_id": WORKER_ID,
            },
        )
        print(
            f"processed {result.get('id')} deck={result.get('deckId')} status={result.get('status')}",
            flush=True,
        )
        return True
    except Exception as exc:
        _record_heartbeat(
            force=True,
            status="error",
            last_error=str(exc),
            metadata={"configuredJobTypes": configured_job_types},
        )
        logger.exception("deck_worker_job_failed", extra={"worker_id": WORKER_ID})
        return False
    finally:
        db.close()


def run_worker(
    *,
    once: bool = False,
    idle_sleep_seconds: float = DEFAULT_IDLE_SLEEP_SECONDS,
    stop_event: threading.Event | None = None,
) -> None:
    stop_event = stop_event or threading.Event()
    configured_job_types = ",".join(sorted(configured_worker_job_types()))
    recovery_only = worker_recovery_only()
    _record_heartbeat(
        force=True,
        status="started",
        metadata={
            "configuredJobTypes": configured_job_types,
            "recoveryOnly": recovery_only,
        },
    )

    while not stop_event.is_set():
        processed = run_once(configured_job_types=configured_job_types, recovery_only=recovery_only)
        if once:
            return
        if not processed:
            stop_event.wait(idle_sleep_seconds)

    _record_heartbeat(force=True, status="stopped", metadata={"configuredJobTypes": configured_job_types})


def _serve_healthcheck(port: int, stop_event: threading.Event) -> None:
    server = ThreadingHTTPServer(("0.0.0.0", port), _WorkerHealthHandler)
    server.timeout = 1.0

    def _shutdown_when_stopped() -> None:
        stop_event.wait()
        server.shutdown()

    threading.Thread(target=_shutdown_when_stopped, daemon=True).start()
    try:
        server.serve_forever(poll_interval=1.0)
    finally:
        server.server_close()


def _apply_worker_role_defaults() -> None:
    app_role = os.getenv("APP_ROLE", "worker").strip().lower().replace("-", "_")
    if not os.getenv("WORKER_KIND"):
        if app_role.startswith("worker_"):
            os.environ["WORKER_KIND"] = app_role.removeprefix("worker_")
        elif app_role == "worker":
            default_kind = os.getenv("DECK_WORKER_KIND")
            if default_kind:
                os.environ["WORKER_KIND"] = default_kind.strip().lower().replace("-", "_")
            else:
                inferred_kind = infer_worker_kind_from_service_name(os.getenv("RAILWAY_SERVICE_NAME"))
                if inferred_kind:
                    os.environ["WORKER_KIND"] = inferred_kind
    if app_role == "stale_job_rescuer":
        os.environ.setdefault("DECK_WORKER_RECOVERY_ONLY", "true")
    if os.getenv("WORKER_KIND") == "stale_job_rescuer":
        os.environ.setdefault("DECK_WORKER_RECOVERY_ONLY", "true")
    if not os.getenv("DECK_WORKER_JOB_TYPES") and os.getenv("WORKER_KIND") and os.getenv("WORKER_KIND") != "stale_job_rescuer":
        os.environ["DECK_WORKER_JOB_TYPES"] = os.getenv("WORKER_KIND", "")


def main() -> None:
    _apply_worker_role_defaults()
    parser = argparse.ArgumentParser(description="Process durable DeckAiStack workflow jobs.")
    parser.add_argument("--once", action="store_true", help="Process at most one queued job and exit.")
    parser.add_argument(
        "--idle-sleep-seconds",
        type=float,
        default=DEFAULT_IDLE_SLEEP_SECONDS,
        help="Sleep duration when no queued jobs are available.",
    )
    args = parser.parse_args()

    if args.once:
        run_worker(once=True, idle_sleep_seconds=args.idle_sleep_seconds)
        return

    stop_event = threading.Event()
    failure: dict[str, str] = {}

    def _handle_signal(_signum: int, _frame: object) -> None:
        logger.info("deck_worker_stop_requested", extra={"signal": _signum, "worker_id": WORKER_ID})
        stop_event.set()

    def _worker_loop() -> None:
        try:
            run_worker(once=False, idle_sleep_seconds=args.idle_sleep_seconds, stop_event=stop_event)
        except BaseException:  # pragma: no cover - defensive, surfaces worker crash to Railway
            failure["traceback"] = traceback.format_exc()
            stop_event.set()
            raise

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    worker_thread = threading.Thread(target=_worker_loop, name="deck-processing-worker", daemon=True)
    worker_thread.start()

    logger.info(
        "deck_worker_started",
        extra={
            "poll_interval_seconds": args.idle_sleep_seconds,
            "worker_id": WORKER_ID,
            "health_port": int(os.environ.get("PORT", "8080")),
        },
    )

    try:
        _serve_healthcheck(int(os.environ.get("PORT", "8080")), stop_event)
    finally:
        stop_event.set()
        worker_thread.join(timeout=5.0)
        if failure.get("traceback"):
            print(failure["traceback"], flush=True)
            raise SystemExit(1)
        logger.info("deck_worker_stopped", extra={"worker_id": WORKER_ID})


if __name__ == "__main__":
    main()
