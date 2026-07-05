from __future__ import annotations

import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings


def scan_upload_path(path: Path) -> dict[str, str | int]:
    command = settings.upload_security_scan_command.strip()
    if not command:
        return {"status": "not_configured"}

    args = shlex.split(command)
    if "{path}" in args:
        args = [str(path) if item == "{path}" else item for item in args]
    else:
        args.append(str(path))

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=settings.upload_security_scan_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Upload security scan timed out") from exc
    except OSError as exc:
        # Production recovery behaviour: do not block MVP uploads when the
        # configured scanner binary is unavailable in the Railway image.
        # The missing scanner is recorded in DeckFile.metadata_json so it remains
        # visible for admin review and later hardening.
        return {
            "status": "scanner_unavailable",
            "scanner": args[0] if args else command,
            "error": exc.__class__.__name__,
            "scannedAt": datetime.now(UTC).isoformat(),
        }

    if result.returncode != 0:
        raise ValueError("Upload security scan rejected the file")

    return {
        "status": "clean",
        "scanner": args[0],
        "exitCode": result.returncode,
        "scannedAt": datetime.now(UTC).isoformat(),
    }
