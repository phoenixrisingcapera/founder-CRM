from __future__ import annotations

CARD_CONTRACT_VERSION = "brand-profile-card-v1"


def attach_card_swatches(profile_payload: dict) -> dict:
    payload = dict(profile_payload)
    slots = [
        ("primary", "Primary", "primaryColor"),
        ("secondary", "Secondary", "secondaryColor"),
        ("accent", "Accent", "accentColor"),
        ("background", "Background", "backgroundColor"),
        ("text", "Text", "textColor"),
    ]
    values = []
    seen = set()
    for role, label, key in slots:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            clean = value.strip()
            values.append({"role": role, "label": label, "value": clean, "field": key})
            seen.add(clean)
    for value in payload.get("palette") or []:
        if len(values) >= 5:
            break
        if isinstance(value, str) and value.strip() and value.strip() not in seen:
            index = len(values) + 1
            clean = value.strip()
            values.append({"role": f"color_{index}", "label": f"Color {index}", "value": clean, "field": "palette"})
            seen.add(clean)
    payload["deterministicMappingVersion"] = CARD_CONTRACT_VERSION
    payload["deterministicSwatches"] = values
    return payload
