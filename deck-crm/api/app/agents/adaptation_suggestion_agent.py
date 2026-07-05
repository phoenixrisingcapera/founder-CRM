from __future__ import annotations


import json

from app.agents.claude_agent_utils import complete_json_with_claude


def run(
    deck_id: str,
    audience_type: str,
    *,
    deck_context: dict | None = None,
    provider_config: dict | None = None,
) -> list[dict[str, str]]:
    if deck_context:
        if provider_config and provider_config.get("provider") == "missing_claude":
            raise ValueError("Claude adaptation suggestions require a workspace Claude key or ANTHROPIC_API_KEY.")
        raw = complete_json_with_claude(
            provider_config=provider_config,
            system="You create reviewable audience adaptation suggestions for pitch decks. Return JSON only.",
            user=(
                "Return a JSON array of 1 to 8 suggestions. Each item must include "
                "slide_id, block_id, title, reason, suggested_text, and audience. "
                "Preserve source-backed facts and do not invent metrics.\n\n"
                f"Target audience: {audience_type}\n"
                f"Deck context:\n{json.dumps(deck_context, ensure_ascii=True)}"
            ),
        )
        if isinstance(raw, list):
            return [_normalize_suggestion(item, deck_id, audience_type) for item in raw if isinstance(item, dict)][:8]

    return [
        {
            "id": "adpt_01",
            "deck_id": deck_id,
            "slide_id": "slide_01",
            "block_id": "block_01",
            "title": "Reframe opening claim for IC review",
            "reason": "Investment Committees prefer quantified operational framing with sourcing.",
            "suggested_text": "Manual triage extends turnaround by 18-24 hours per patient in sampled workflows, creating measurable delay and revenue leakage.",
            "status": "pending",
            "audience": audience_type,
        }
    ]


def _normalize_suggestion(item: dict, deck_id: str, audience_type: str) -> dict[str, str]:
    return {
        "id": str(item.get("id") or ""),
        "deck_id": deck_id,
        "slide_id": str(item.get("slide_id") or ""),
        "block_id": str(item.get("block_id") or ""),
        "title": str(item.get("title") or "Audience adaptation")[:180],
        "reason": str(item.get("reason") or "Improves audience fit while keeping the change reviewable.")[:1200],
        "suggested_text": str(item.get("suggested_text") or "")[:4000],
        "status": "pending",
        "audience": str(item.get("audience") or audience_type)[:120],
    }
