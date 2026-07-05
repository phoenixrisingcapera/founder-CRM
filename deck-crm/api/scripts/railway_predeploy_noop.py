#!/usr/bin/env python3
"""Railway pre-deploy no-op.

Schema work is intentionally handled by scripts/start_railway.py at runtime.
Railway UI can keep a pre-deploy command pointed at this script without racing
or duplicating Alembic migrations.
"""

from __future__ import annotations


def main() -> int:
    print("Railway pre-deploy no-op: migrations run from scripts/start_railway.py", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
