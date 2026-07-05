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


async def generate_venture_artifact(
    *,
    goal_title: str,
    company_name: str | None,
    person_name: str | None,
    opportunity_title: str | None,
    score_summary: str,
    instruction: str | None,
    api_key: str | None,
    provider: str | None = None,
) -> tuple[str | None, str | None, str]:
    resolved_key = api_key or settings.openai_api_key or settings.openrouter_api_key
    if not resolved_key:
        markdown = (
            f"# Founder Brief\n\n"
            f"## Goal\n{goal_title}\n\n"
            f"## Context\n"
            f"- Person: {person_name or 'Not linked'}\n"
            f"- Company: {company_name or 'Not linked'}\n"
            f"- Opportunity: {opportunity_title or 'Not linked'}\n\n"
            f"## Deterministic Score Summary\n{score_summary}\n\n"
            f"## Recommended Action\n"
            f"Use this score to decide the next outreach, warm intro request, or diligence step.\n"
        )
        return None, None, markdown

    chosen_provider, model, resolved_key, url, headers = _resolve_provider(api_key, provider)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You create concise founder CRM briefs. "
                    "Return markdown with sections: Goal, Context, Score Analysis, Missing Data, Next Action."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Goal: {goal_title}\n"
                    f"Person: {person_name or 'n/a'}\n"
                    f"Company: {company_name or 'n/a'}\n"
                    f"Opportunity: {opportunity_title or 'n/a'}\n"
                    f"Score Summary: {score_summary}\n"
                    f"Instruction: {instruction or 'Write the founder brief.'}"
                ),
            },
        ],
        "temperature": 0.3,
    }
    if chosen_provider == "openrouter":
        headers["HTTP-Referer"] = "https://aistack.local"
        headers["X-Title"] = "AiStack Founder CRM"

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, headers=headers, content=json.dumps(payload))
        response.raise_for_status()
        body = response.json()

    message = body["choices"][0]["message"]["content"]
    if isinstance(message, list):
        message = "\n".join(part.get("text", "") for part in message if isinstance(part, dict))
    return chosen_provider, model, (message or "").strip()


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
