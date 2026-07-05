from __future__ import annotations

import json
from urllib import error as url_error
from urllib import request as url_request

from app.ai.provider import AIProvider
from app.core.config import settings


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def extract_openai_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"]
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text
    raise ValueError("OpenAI response did not include a text payload.")


def call_openai_response(
    *,
    api_key: str,
    model: str,
    system: str,
    user: str,
    timeout: int | None = None,
    max_output_tokens: int | None = None,
    response_format: dict | None = None,
) -> dict:
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for OpenAI generation.")

    request_payload: dict = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user}],
            },
        ],
    }
    if max_output_tokens is not None:
        request_payload["max_output_tokens"] = max(1, max_output_tokens)
    if response_format is not None:
        request_payload["text"] = {"format": response_format}

    http_request = url_request.Request(
        url=OPENAI_RESPONSES_URL,
        data=json.dumps(request_payload).encode("utf-8"),
        headers={"authorization": f"Bearer {api_key}", "content-type": "application/json"},
        method="POST",
    )
    try:
        with url_request.urlopen(http_request, timeout=_effective_timeout(timeout)) as response:
            return json.loads(response.read().decode("utf-8"))
    except url_error.HTTPError as exc:
        raise ValueError(f"OpenAI generation failed with status {exc.code}") from exc
    except url_error.URLError as exc:
        raise ValueError("OpenAI generation failed due to a network error") from exc


def _effective_timeout(requested_timeout: int | None) -> int:
    configured_timeout = max(1, settings.openai_timeout_seconds)
    if requested_timeout is None:
        return configured_timeout
    return max(1, min(requested_timeout, configured_timeout))


class OpenAIProvider(AIProvider):
    def complete(self, system: str, user: str) -> dict[str, str]:
        response = call_openai_response(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            system=system,
            user=user,
        )
        return {"text": extract_openai_text(response)}
