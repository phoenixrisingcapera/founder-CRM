from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.brand_profile_card_contract import CARD_CONTRACT_VERSION, attach_card_swatches


def main() -> None:
    payload = attach_card_swatches(
        {
            "primaryColor": "#111111",
            "secondaryColor": "#222222",
            "accentColor": "#333333",
            "backgroundColor": "#444444",
            "textColor": "#555555",
            "palette": ["#111111", "#222222", "#333333", "#444444", "#555555"],
        }
    )
    assert payload["deterministicMappingVersion"] == CARD_CONTRACT_VERSION
    assert len(payload["deterministicSwatches"]) == 5
    assert payload["deterministicSwatches"][0]["label"] == "Primary"
    assert payload["deterministicSwatches"][0]["value"] == "#111111"
    assert payload["deterministicSwatches"][2]["role"] == "accent"
    print("Brand profile card backend contract verified.")


if __name__ == "__main__":
    main()
