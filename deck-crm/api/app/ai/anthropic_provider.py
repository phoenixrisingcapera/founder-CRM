from __future__ import annotations

import json
import time
from urllib import error as url_error
from urllib import request as url_request

from app.ai.provider import AIProvider
from app.core.config import settings


ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}


def extract_anthropic_text(payload: dict) -> str:
    for block in payload.get("content", []):
        if block.get("type") == "text" and block.get("text"):
            return str(block["text"])
    raise ValueError("Anthropic response did not include a text payload.")


def call_anthropic_message(
    *,
    api_key: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int | None = None,
    timeout: int | None = None,
) -> dict:
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is required for Claude generation.")

    request_payload = {
        "model": model,
        "max_tokens": max_tokens or settings.anthropic_max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    http_request = url_request.Request(
        url=ANTHROPIC_MESSAGES_URL,
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    effective_timeout = _effective_timeout(timeout)
    attempts = settings.anthropic_max_retries + 1
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with url_request.urlopen(http_request, timeout=effective_timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except url_error.HTTPError as exc:
            last_error = exc
            if exc.code not in RETRYABLE_HTTP_STATUSES or attempt == attempts - 1:
                raise ValueError(f"Anthropic generation failed with status {exc.code}") from exc
            _sleep_before_retry()
        except url_error.URLError as exc:
            last_error = exc
            if attempt == attempts - 1:
                raise ValueError("Anthropic generation failed due to a network error") from exc
            _sleep_before_retry()
    raise ValueError("Anthropic generation failed") from last_error


def _effective_timeout(requested_timeout: int | None) -> int:
    configured_timeout = max(1, settings.anthropic_timeout_seconds)
    if requested_timeout is None:
        return configured_timeout
    return max(1, min(requested_timeout, configured_timeout))


def _sleep_before_retry() -> None:
    delay = settings.anthropic_retry_delay_seconds
    if delay > 0:
        time.sleep(delay)


class AnthropicProvider(AIProvider):
    def complete(self, system: str, user: str) -> dict[str, str]:
        response = call_anthropic_message(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            system=system,
            user=user,
        )
        return {"text": extract_anthropic_text(response)}
