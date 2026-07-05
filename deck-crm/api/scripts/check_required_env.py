#!/usr/bin/env python3
"""Validate DeckAiStack Railway production environment variables.

Usage:
  python scripts/check_required_env.py
  python scripts/check_required_env.py --env-file .env.railway.required

The script intentionally avoids importing the app settings until after it has
reported simple missing/placeholder values. That makes it useful inside Railway
shells even when app startup is failing.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.railway_env import (
    DATABASE_ENV_ALIASES,
    STORAGE_ACCESS_KEY_ENV_ALIASES,
    STORAGE_BUCKET_ENV_ALIASES,
    STORAGE_ENDPOINT_ENV_ALIASES,
    STORAGE_REGION_ENV_ALIASES,
    STORAGE_SECRET_KEY_ENV_ALIASES,
)

PLACEHOLDER_RE = re.compile(r"^(REPLACE_ME|CHANGE_ME|TODO|<.*>|your_|real railway postgres url)", re.IGNORECASE)

DATABASE_CANDIDATES = list(DATABASE_ENV_ALIASES)
STORAGE_BUCKET_CANDIDATES = list(STORAGE_BUCKET_ENV_ALIASES)
STORAGE_REGION_CANDIDATES = list(STORAGE_REGION_ENV_ALIASES)
STORAGE_ENDPOINT_CANDIDATES = list(STORAGE_ENDPOINT_ENV_ALIASES)
STORAGE_ACCESS_CANDIDATES = list(STORAGE_ACCESS_KEY_ENV_ALIASES)
STORAGE_SECRET_CANDIDATES = list(STORAGE_SECRET_KEY_ENV_ALIASES)
AI_KEY_CANDIDATES = ["OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def load_env_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Env file not found: {path}")
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def value(name: str) -> str:
    return os.getenv(name, "").strip()


def is_placeholder(raw: str) -> bool:
    if not raw:
        return True
    return bool(PLACEHOLDER_RE.search(raw)) or "REPLACE_ME" in raw or "change-me" in raw.lower()


def first_real(names: list[str]) -> tuple[str | None, str | None]:
    for name in names:
        raw = value(name)
        if raw and not is_placeholder(raw):
            return name, raw
    return None, None


def bool_value(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def valid_db_url(raw: str) -> bool:
    if is_placeholder(raw):
        return False
    if raw.startswith("sqlite"):
        return False
    candidate = raw.replace("postgres://", "postgresql://", 1)
    if not candidate.startswith(("postgresql://", "postgresql+psycopg://")):
        return False
    parsed = urlsplit(candidate)
    return bool(parsed.scheme and parsed.netloc)


def valid_fernet_key(raw: str) -> bool:
    if is_placeholder(raw):
        return False
    try:
        decoded = base64.urlsafe_b64decode(raw.encode("utf-8"))
    except (binascii.Error, ValueError):
        return False
    return len(decoded) == 32


def check_required_scalar(name: str, *, min_length: int = 1, allow_placeholder: bool = False) -> Check:
    raw = value(name)
    if not raw:
        return Check(name, False, "missing")
    if not allow_placeholder and is_placeholder(raw):
        return Check(name, False, "placeholder value")
    if len(raw) < min_length:
        return Check(name, False, f"too short: expected at least {min_length} chars")
    return Check(name, True, "set")


def check_one_of(label: str, names: list[str]) -> Check:
    found_name, found_value = first_real(names)
    if found_name:
        safe = "configured"
        if label == "DATABASE_URL" and not valid_db_url(found_value or ""):
            return Check(label, False, f"{found_name} is set but not a valid Postgres URL")
        return Check(label, True, f"using {found_name}: {safe}")
    return Check(label, False, f"missing one of: {', '.join(names)}")


def run_checks() -> list[Check]:
    checks: list[Check] = []

    checks.append(check_required_scalar("APP_ENV"))
    if value("APP_ENV").lower() != "production":
        checks.append(Check("APP_ENV=production", False, f"current value: {value('APP_ENV') or '<missing>'}"))
    else:
        checks.append(Check("APP_ENV=production", True, "production"))

    checks.append(check_one_of("DATABASE_URL", DATABASE_CANDIDATES))
    checks.append(check_required_scalar("AUTH_SECRET_KEY", min_length=32))
    checks.append(check_required_scalar("AUTH_SECRET_KEY_ID", min_length=3))

    fernet = value("WORKSPACE_AI_FERNET_KEY")
    checks.append(Check("WORKSPACE_AI_FERNET_KEY", valid_fernet_key(fernet), "valid Fernet key" if valid_fernet_key(fernet) else "missing/invalid Fernet key"))
    checks.append(check_required_scalar("WORKSPACE_AI_FERNET_KEY_VERSION", min_length=3))

    signup = value("PUBLIC_SIGNUP_ENABLED")
    checks.append(Check("PUBLIC_SIGNUP_ENABLED", bool_value(signup), f"current value: {signup or '<missing>'}; set true for testers"))

    storage_backend = value("UPLOAD_STORAGE_BACKEND") or value("DECK_AISTACK_STORAGE_PROVIDER")
    checks.append(Check("UPLOAD_STORAGE_BACKEND", storage_backend.lower() in {"s3", "supabase"}, f"current value: {storage_backend or '<missing>'}; production must not be local"))
    if storage_backend.lower() == "s3" or value("DECK_AISTACK_STORAGE_PROVIDER").lower() == "s3":
        checks.append(check_one_of("S3_BUCKET", STORAGE_BUCKET_CANDIDATES))
        checks.append(check_one_of("S3_REGION", STORAGE_REGION_CANDIDATES))
        checks.append(check_one_of("S3_ACCESS_KEY", STORAGE_ACCESS_CANDIDATES))
        checks.append(check_one_of("S3_SECRET_KEY", STORAGE_SECRET_CANDIDATES))
        endpoint_name, _endpoint = first_real(STORAGE_ENDPOINT_CANDIDATES)
        checks.append(Check("S3_ENDPOINT", True, f"using {endpoint_name}" if endpoint_name else "optional unless bucket provider requires it"))

    checks.append(check_one_of("AI_PROVIDER_KEY", AI_KEY_CANDIDATES))

    origins = value("ALLOWED_ORIGINS") or value("CORS_ALLOWED_ORIGINS") or value("CORS_ORIGIN")
    checks.append(Check("ALLOWED_ORIGINS", "https://deck.aistack.codes" in origins, f"current value: {origins or '<missing>'}"))

    return checks


def print_report(checks: list[Check]) -> int:
    print("\nDeckAiStack Railway env audit\n")
    for item in checks:
        print(f"[{'PASS' if item.ok else 'FAIL'}] {item.name}: {item.detail}")
    failures = [item for item in checks if not item.ok]
    print("")
    if failures:
        print("Missing or broken variables:")
        for item in failures:
            print(f"- {item.name}: {item.detail}")
        return 1
    print("All required production variables look present. If deployment still fails, inspect app logs next.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Railway production env vars for DeckAiStack backend.")
    parser.add_argument("--env-file", default="", help="Optional .env file to load before checking, e.g. .env.railway.required")
    args = parser.parse_args()
    if args.env_file:
        load_env_file(Path(args.env_file))
    return print_report(run_checks())


if __name__ == "__main__":
    raise SystemExit(main())
