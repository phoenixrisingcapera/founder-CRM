from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from app.core.railway_env import apply_railway_env_aliases

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = "8080"


def _truthy(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_railway() -> bool:
    return any(
        os.getenv(name)
        for name in (
            "RAILWAY_ENVIRONMENT",
            "RAILWAY_ENVIRONMENT_ID",
            "RAILWAY_SERVICE_NAME",
            "RAILWAY_PROJECT_ID",
        )
    )


def _prepare_runtime_defaults() -> None:
    """Set safe runtime defaults required before importing app settings.

    The current upload path validates file extension, MIME type, and upload size in
    Python before persistence. A scanner command is not invoked by the active upload
    service, but older production settings still require the variable to exist. Set
    a harmless sentinel here so Railway deployments do not fail startup because of
    an unused scanner knob.
    """

    os.environ.setdefault("UPLOAD_SECURITY_SCAN_COMMAND", "disabled")
    apply_railway_env_aliases()


def _run_runtime_schema_bootstrap(migration_env: dict[str, str]) -> None:
    subprocess.check_call([sys.executable, "scripts/ensure_runtime_schema.py"], env=migration_env)


def _run_migrations_if_enabled() -> None:
    if not _truthy(os.getenv("RUN_MIGRATIONS_ON_STARTUP"), default=True):
        print("Skipping schema bootstrap because RUN_MIGRATIONS_ON_STARTUP is false.", flush=True)
        return

    migration_env = {**os.environ, "APP_ROLE": "migration"}
    run_alembic = _truthy(
        os.getenv("RUN_ALEMBIC_MIGRATIONS_ON_STARTUP"),
        default=True,
    )

    if not run_alembic:
        print(
            "Skipping Alembic on Railway startup; running runtime schema bootstrap only.",
            flush=True,
        )
        _run_runtime_schema_bootstrap(migration_env)
        return

    print("Running Alembic migrations before starting service.", flush=True)
    allow_migration_failure = _truthy(
        os.getenv("ALLOW_MIGRATION_FAILURE_ON_STARTUP"),
        default=_is_railway(),
    )

    try:
        subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "heads"], env=migration_env)
    except subprocess.CalledProcessError as exc:
        if not allow_migration_failure:
            raise
        print(
            "WARNING: Alembic upgrade failed during Railway startup. "
            "Running runtime schema bootstrap and continuing so the API can start. "
            f"Exit code: {exc.returncode}",
            flush=True,
        )

    _run_runtime_schema_bootstrap(migration_env)


def _exec_api() -> None:
    port = os.getenv("PORT", DEFAULT_PORT)
    host = os.getenv("HOST", DEFAULT_HOST)
    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            host,
            "--port",
            port,
        ],
    )


def _exec_worker() -> None:
    os.execvp(sys.executable, [sys.executable, "scripts/deck_processing_worker.py"])


def main() -> None:
    _prepare_runtime_defaults()
    app_role = os.getenv("APP_ROLE", "api").strip().lower()

    if app_role == "worker" or app_role.startswith("worker-"):
        # Workers should not race API deployments for schema changes by default.
        if _truthy(os.getenv("RUN_WORKER_MIGRATIONS_ON_STARTUP"), default=False):
            _run_migrations_if_enabled()
        _exec_worker()
        return

    _run_migrations_if_enabled()
    _exec_api()


if __name__ == "__main__":
    main()
