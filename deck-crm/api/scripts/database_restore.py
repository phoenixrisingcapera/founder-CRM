from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from scripts.database_backup import masked_url, postgres_cli_url


RESTORE_CONFIRMATION = "restore-deck-aistack-codes-database"


def build_pg_restore_command(database_url: str, input_path: Path) -> list[str]:
    return [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-acl",
        f"--dbname={postgres_cli_url(database_url)}",
        str(input_path),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore a PostgreSQL custom-format backup.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL") or settings.database_url)
    parser.add_argument("--confirm", default="")
    parser.add_argument("--confirm-production", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.confirm != RESTORE_CONFIRMATION:
        print(f"Refusing restore without --confirm {RESTORE_CONFIRMATION!r}.", file=sys.stderr)
        return 2
    if settings.is_production and not args.confirm_production:
        print("Refusing production restore without --confirm-production.", file=sys.stderr)
        return 2
    if not args.input.is_file():
        print(f"Backup file not found: {args.input}", file=sys.stderr)
        return 2

    command = build_pg_restore_command(args.database_url, args.input)
    print(f"Restoring database {masked_url(args.database_url)}")
    print(f"Input: {args.input}")
    subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
