from __future__ import annotations

import json
from urllib import error as url_error
from urllib import request as url_request

from app.ai.provider import AIProvider
from app.core.config import settings


OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


def extract_openrouter_text(payload: dict) -> str:
    for choice in payload.get("choices", []):
        message = choice.get("message") if isinstance(choice, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            text = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and isinstance(block.get("text"), str)
            ).strip()
            if text:
                return text
    raise ValueError("OpenRouter response did not include a text payload.")


def call_openrouter_chat_completion(
    *,
    api_key: str,
    model: str,
    system: str,
    user: str,
    timeout: int | None = None,
    max_tokens: int | None = None,
    response_format: dict | None = None,
) -> dict:
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is required for OpenRouter generation.")

    request_payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if max_tokens is not None:
        request_payload["max_tokens"] = max(1, max_tokens)
    if response_format is not None:
        request_payload["response_format"] = response_format

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if settings.openrouter_site_url:
        headers["HTTP-Referer"] = settings.openrouter_site_url
    if settings.openrouter_app_name:
        headers["X-Title"] = settings.openrouter_app_name

    http_request = url_request.Request(
        url=OPENROUTER_CHAT_COMPLETIONS_URL,
        data=json.dumps(request_payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with url_request.urlopen(http_request, timeout=_effective_timeout(timeout)) as response:
            return json.loads(response.read().decode("utf-8"))
    except url_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"OpenRouter generation failed with status {exc.code}: {detail[:400]}") from exc
    except url_error.URLError as exc:
        raise ValueError("OpenRouter generation failed due to a network error") from exc


def _effective_timeout(requested_timeout: int | None) -> int:
    configured_timeout = max(1, settings.openrouter_timeout_seconds)
    if requested_timeout is None:
        return configured_timeout
    return max(1, min(requested_timeout, configured_timeout))


class OpenRouterProvider(AIProvider):
    def complete(self, system: str, user: str) -> dict[str, str]:
        response = call_openrouter_chat_completion(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            system=system,
            user=user,
        )
        return {"text": extract_openrouter_text(response)}
