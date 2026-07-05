from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


def postgres_cli_url(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    return database_url


def masked_url(database_url: str) -> str:
    parts = urlsplit(postgres_cli_url(database_url))
    if "@" not in parts.netloc:
        return postgres_cli_url(database_url)
    credentials, host = parts.netloc.rsplit("@", 1)
    username = credentials.split(":", 1)[0]
    return urlunsplit((parts.scheme, f"{username}:***@{host}", parts.path, parts.query, parts.fragment))


def default_backup_path() -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return Path("backups") / f"deck-aistack-codes-{settings.app_env}-{timestamp}.dump"


def build_pg_dump_command(database_url: str, output_path: Path) -> list[str]:
    return [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-acl",
        f"--file={str(output_path)}",
        postgres_cli_url(database_url),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a PostgreSQL custom-format backup.")
    parser.add_argument("--output", type=Path, default=default_backup_path())
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL") or settings.database_url)
    parser.add_argument("--confirm-production", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if settings.is_production and not args.confirm_production:
        print("Refusing production backup without --confirm-production.", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = build_pg_dump_command(args.database_url, args.output)
    print(f"Creating database backup from {masked_url(args.database_url)}")
    print(f"Output: {args.output}")
    subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
