from __future__ import annotations

import json
from typing import Any

from app.ai.anthropic_provider import call_anthropic_message, extract_anthropic_text
from app.core.config import settings


def extract_json_payload(raw_text: str) -> Any:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    start_object = text.find("{")
    start_array = text.find("[")
    starts = [value for value in [start_object, start_array] if value != -1]
    if not starts:
        raise ValueError("Claude response did not contain JSON.")
    start = min(starts)
    end = text.rfind("}") if text[start] == "{" else text.rfind("]")
    if end == -1 or end <= start:
        raise ValueError("Claude response contained incomplete JSON.")
    return json.loads(text[start : end + 1])


def complete_json_with_claude(
    *,
    provider_config: dict | None,
    system: str,
    user: str,
    max_tokens: int = 1800,
) -> Any | None:
    if not provider_config or provider_config.get("provider") != "anthropic":
        return None
    api_key = provider_config.get("apiKey")
    model = provider_config.get("model") or settings.anthropic_model
    if not api_key:
        return None
    response = call_anthropic_message(
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        system=system,
        user=user,
        timeout=60,
    )
    return extract_json_payload(extract_anthropic_text(response))
