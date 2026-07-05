from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.routes.product_runtime_hardening import _smart_deck_debug_payload, _with_smart_deck_debug
from app.db.models import Deck
from app.db.session import SessionLocal
from app.services.deck_processing_visibility_service import get_deck_processing_visibility


def _fail(message: str, payload: dict[str, Any] | None = None) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    if payload is not None:
        print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Smart Deck visualizer readiness for a deployed deck.")
    parser.add_argument("deck_id", help="Deck id to verify, for example deck_123")
    parser.add_argument(
        "--allow-not-ready",
        action="store_true",
        help="Print the debug payload but do not fail when the visualizer is not ready yet.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        deck = db.query(Deck).filter(Deck.id == args.deck_id).one_or_none()
        if deck is None:
            return _fail(f"Deck not found: {args.deck_id}")

        visibility = get_deck_processing_visibility(db, args.deck_id)
        if visibility is None:
            return _fail(f"Processing visibility not found: {args.deck_id}")

        payload = _with_smart_deck_debug(visibility, _smart_deck_debug_payload(db, deck))
        print(json.dumps(payload, indent=2, sort_keys=True))

        smart_deck = payload.get("smartDeck") if isinstance(payload.get("smartDeck"), dict) else {}
        checks = {
            "nextAction": payload.get("nextAction"),
            "canOpenSmartDeck": payload.get("canOpenSmartDeck"),
            "generatedSlideCount": smart_deck.get("generatedSlideCount"),
            "activeGeneratedSlideId": smart_deck.get("activeGeneratedSlideId"),
            "renderSchemaElementCount": smart_deck.get("renderSchemaElementCount"),
            "hasRenderableSchema": smart_deck.get("hasRenderableSchema"),
        }

        ready = (
            checks["nextAction"] == "open_smart_deck"
            and checks["canOpenSmartDeck"] is True
            and isinstance(checks["generatedSlideCount"], int)
            and checks["generatedSlideCount"] > 0
            and bool(checks["activeGeneratedSlideId"])
            and isinstance(checks["renderSchemaElementCount"], int)
            and checks["renderSchemaElementCount"] > 0
            and checks["hasRenderableSchema"] is True
        )
        if not ready and not args.allow_not_ready:
            return _fail("Smart Deck visualizer contract is not ready.", checks)

        print("PASS: Smart Deck visualizer contract is ready." if ready else "INFO: Smart Deck visualizer is not ready yet.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
