from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal
from app.services.deployment_readiness_service import get_deployment_readiness


def main() -> int:
    db = SessionLocal()
    try:
        result = get_deployment_readiness(db)
    finally:
        db.close()

    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("summary", {}).get("readyForTesterTraffic") else 1


if __name__ == "__main__":
    raise SystemExit(main())
