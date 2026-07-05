#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ALLOWED_ENV_NAMES = {
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONUNBUFFERED",
    "PIP_NO_CACHE_DIR",
}


def main() -> int:
    dockerfile = Path("Dockerfile")
    if not dockerfile.exists():
        print("FAIL Dockerfile missing")
        return 1

    failures: list[str] = []
    for line_number, line in enumerate(dockerfile.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("ARG "):
            failures.append(f"line {line_number}: Dockerfile must not use ARG")
        if stripped.startswith("ENV "):
            tokens = stripped.replace("\\", " ").split()
            for token in tokens[1:]:
                if "=" not in token:
                    continue
                key = token.split("=", 1)[0]
                if key not in ALLOWED_ENV_NAMES:
                    failures.append(f"line {line_number}: unexpected Dockerfile ENV key: {key}")

    if failures:
        print("Docker runtime-only env guard: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Docker runtime-only env guard: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
