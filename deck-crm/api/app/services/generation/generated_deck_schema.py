from __future__ import annotations

import json
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[4] / "deck_aistack_codes_api_prompt_package"
SCHEMA_PATH = PACKAGE_ROOT / "schemas" / "generated_deck.schema.json"


def load_generated_deck_schema() -> dict:
    if SCHEMA_PATH.exists():
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    # Fallback keeps local generation available even if the package moves.
    return {
        "type": "object",
        "required": ["status", "deck", "slides", "quality"],
    }
