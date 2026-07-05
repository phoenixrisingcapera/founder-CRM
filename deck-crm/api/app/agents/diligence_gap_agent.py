from __future__ import annotations


import json

from app.agents.claude_agent_utils import complete_json_with_claude


def run(deck_id: str, *, deck_context: dict | None = None, provider_config: dict | None = None) -> list[dict[str, str]]:
    if deck_context:
        if provider_config and provider_config.get("provider") == "missing_claude":
            raise ValueError("Claude diligence analysis requires a workspace Claude key or ANTHROPIC_API_KEY.")
        raw = complete_json_with_claude(
            provider_config=provider_config,
            system="You detect investor diligence gaps in pitch decks. Return JSON only.",
            user=(
                "Return a JSON array of 1 to 8 findings. Each item must include "
                "slide_id, block_id, title, detail, severity, and category. "
                "severity must be low, medium, or high. Use only provided deck context.\n\n"
                f"Deck context:\n{json.dumps(deck_context, ensure_ascii=True)}"
            ),
        )
        if isinstance(raw, list):
            return [_normalize_finding(item, deck_id) for item in raw if isinstance(item, dict)][:8]

    return [
        {
            "id": "finding_01",
            "deck_id": deck_id,
            "slide_id": "slide_01",
            "block_id": "block_02",
            "title": "Problem claim needs primary evidence",
            "detail": "The workflow fragmentation claim needs benchmark data or source notes.",
            "severity": "high",
            "category": "missing evidence",
        }
    ]


def _normalize_finding(item: dict, deck_id: str) -> dict[str, str]:
    severity = str(item.get("severity") or "medium").lower()
    if severity not in {"low", "medium", "high"}:
        severity = "medium"
    return {
        "id": str(item.get("id") or ""),
        "deck_id": deck_id,
        "slide_id": str(item.get("slide_id") or ""),
        "block_id": str(item.get("block_id") or ""),
        "title": str(item.get("title") or "Diligence gap")[:180],
        "detail": str(item.get("detail") or "Review this claim before relying on it.")[:1200],
        "severity": severity,
        "category": str(item.get("category") or "missing evidence")[:120],
    }
