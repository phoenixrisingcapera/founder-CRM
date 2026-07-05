import json

import httpx

from app.core.config import settings


async def generate_deck_improvement(
    *,
    audience_label: str,
    instruction: str,
    slide_text: str,
    api_key: str | None,
    provider: str | None = None,
) -> tuple[str, str, str]:
    provider, model, resolved_key, url, headers = _resolve_provider(api_key, provider)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You improve investor deck narratives for founders. "
                    "Return markdown with sections: Narrative, Slide Edits, Risks, Next Meeting Angle."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Audience: {audience_label}\n"
                    f"Instruction: {instruction}\n"
                    f"Deck content:\n{slide_text[:12000]}"
                ),
            },
        ],
        "temperature": 0.4,
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://aistack.local"
        headers["X-Title"] = "AiStack Founder CRM"

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, headers=headers, content=json.dumps(payload))
        response.raise_for_status()
        body = response.json()

    message = body["choices"][0]["message"]["content"]
    if isinstance(message, list):
        message = "\n".join(part.get("text", "") for part in message if isinstance(part, dict))
    return provider, model, (message or "").strip()


def _resolve_provider(api_key: str | None, provider: str | None) -> tuple[str, str, str, str, dict[str, str]]:
    resolved_provider = provider or ("openai" if api_key and api_key.startswith("sk-") else None)
    if resolved_provider == "openai" or settings.openai_api_key or (api_key and api_key.startswith("sk-")):
        resolved_key = api_key or settings.openai_api_key
        if not resolved_key:
            raise ValueError("Missing OpenAI API key")
        return (
            "openai",
            settings.openai_model,
            resolved_key,
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {resolved_key}", "Content-Type": "application/json"},
        )

    resolved_key = api_key or settings.openrouter_api_key
    if not resolved_key:
        raise ValueError("No system key configured. Provide your own OpenAI or OpenRouter API key.")
    return (
        "openrouter",
        settings.openrouter_model,
        resolved_key,
        "https://openrouter.ai/api/v1/chat/completions",
        {"Authorization": f"Bearer {resolved_key}", "Content-Type": "application/json"},
    )
