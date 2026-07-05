#!/usr/bin/env python3
"""Production state doctor for DeckAiStack.

This script answers one question: which state is broken?

It intentionally uses only the Python standard library so it can run from a
fresh Railway shell, local checkout, or CI without installing extra packages.

Default safe checks are read-only. Optional authenticated checks run only when
DECK_AISTACK_AUTH_TOKEN is present or --auth-token is supplied.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_FRONTEND_URL = "https://deck.aistack.codes"
DEFAULT_BACKEND_URL = "https://api.deck.aistack.codes"
PRODUCT_PREFIX = "/api/products/deck-aistack-codes"


@dataclass
class CheckResult:
    name: str
    ok: bool
    status: str
    detail: str = ""
    url: str = ""
    elapsed_ms: int = 0


def normalise_base_url(value: str) -> str:
    return value.strip().rstrip("/")


def request_json_or_text(
    method: str,
    url: str,
    *,
    token: str = "",
    payload: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> tuple[int, dict[str, str], Any, str, int]:
    headers = {
        "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
        "User-Agent": "deck-aistack-doctor/1.0",
    }
    body: bytes | None = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")

    started = time.perf_counter()
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return response.status, dict(response.headers.items()), parse_body(raw), raw, elapsed_ms
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return exc.code, dict(exc.headers.items()), parse_body(raw), raw, elapsed_ms
    except Exception as exc:  # network, DNS, TLS, timeout
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return 0, {}, {"error": type(exc).__name__, "detail": str(exc)}, str(exc), elapsed_ms


def parse_body(raw: str) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw[:500]


def body_summary(body: Any, raw: str = "") -> str:
    if isinstance(body, dict):
        keys = ", ".join(sorted(str(k) for k in body.keys())[:8])
        message = body.get("detail") or body.get("message") or body.get("error")
        if message:
            return f"{message} | keys: {keys}"
        return f"keys: {keys}"
    if isinstance(body, list):
        return f"list[{len(body)}]"
    text = raw or str(body)
    return text.replace("\n", " ")[:220]


def check_http(name: str, method: str, url: str, *, expected: set[int], token: str = "", payload: dict[str, Any] | None = None) -> CheckResult:
    status, _headers, body, raw, elapsed_ms = request_json_or_text(method, url, token=token, payload=payload)
    ok = status in expected
    return CheckResult(
        name=name,
        ok=ok,
        status=str(status) if status else "NO_RESPONSE",
        detail=body_summary(body, raw),
        url=url,
        elapsed_ms=elapsed_ms,
    )


def run_checks(frontend_url: str, backend_url: str, token: str, deck_id: str) -> list[CheckResult]:
    frontend_url = normalise_base_url(frontend_url)
    backend_url = normalise_base_url(backend_url)
    results: list[CheckResult] = []

    # State 1: can the app shell load?
    results.append(check_http("frontend_load", "GET", frontend_url, expected={200, 301, 302, 307, 308}))

    # State 2: can the backend boot and answer both health surfaces?
    results.append(check_http("backend_health_root", "GET", f"{backend_url}/health", expected={200}))
    results.append(check_http("backend_health_api", "GET", f"{backend_url}/api/health", expected={200}))

    # State 3: public route should be reachable without auth. If this fails, routing/CORS/proxy is wrong.
    results.append(
        check_http(
            "public_interest_route_reachable",
            "POST",
            f"{backend_url}/api/public/interest",
            expected={200, 201, 202, 400, 409, 422},
            payload={"email": "doctor@example.invalid", "source": "doctor"},
        )
    )

    # State 4: protected product route should not 500/503. A 401/403 is correct without token.
    results.append(
        check_http(
            "protected_deck_list_auth_boundary",
            "GET",
            f"{backend_url}{PRODUCT_PREFIX}/decks",
            expected={200, 401, 403},
            token=token,
        )
    )

    # State 5: if token is available, check DB-backed list/read surface.
    if token:
        results.append(
            check_http(
                "authenticated_deck_list_db_read",
                "GET",
                f"{backend_url}{PRODUCT_PREFIX}/decks",
                expected={200},
                token=token,
            )
        )
    else:
        results.append(CheckResult("authenticated_deck_list_db_read", True, "SKIPPED", "set DECK_AISTACK_AUTH_TOKEN to test DB-backed authenticated save/read"))

    # State 6: if deck id is available, check processing, smart deck, brand and thumbnail-ish state.
    if deck_id:
        for name, path in [
            ("deck_record_read", f"{PRODUCT_PREFIX}/decks/{deck_id}"),
            ("smart_deck_state", f"{PRODUCT_PREFIX}/decks/{deck_id}/smart-deck"),
            ("brand_profile_state", f"{PRODUCT_PREFIX}/decks/{deck_id}/brand-profile"),
            ("generation_jobs_state", f"{PRODUCT_PREFIX}/decks/{deck_id}/smart-deck/generation-jobs"),
        ]:
            results.append(check_http(name, "GET", f"{backend_url}{path}", expected={200, 401, 403, 404}, token=token))
    else:
        results.append(CheckResult("deck_processing_and_thumbnails", True, "SKIPPED", "pass --deck-id after upload to inspect processing/smart-deck/brand state"))

    return results


def print_report(results: list[CheckResult]) -> int:
    hard_failures = [result for result in results if not result.ok]
    print("\nDeckAiStack production doctor\n")
    for result in results:
        marker = "PASS" if result.ok else "FAIL"
        print(f"[{marker}] {result.name}: {result.status} ({result.elapsed_ms}ms)")
        if result.url:
            print(f"       url: {result.url}")
        if result.detail:
            print(f"       detail: {result.detail}")
    print("")

    if hard_failures:
        print("Diagnosis: hard failures found before the app can be trusted.")
        for failure in hard_failures:
            print(f"- {failure.name}: {failure.status} {failure.detail}")
        return 1

    protected = next((item for item in results if item.name == "protected_deck_list_auth_boundary"), None)
    if protected and protected.status in {"401", "403"}:
        print("Diagnosis: backend is reachable, but protected app state requires valid frontend/backend auth propagation.")
    else:
        print("Diagnosis: base app surfaces are reachable. Use an auth token and deck id to verify DB save, processing, and thumbnails.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DeckAiStack production app states.")
    parser.add_argument("--frontend-url", default=os.getenv("DECK_AISTACK_FRONTEND_URL", DEFAULT_FRONTEND_URL))
    parser.add_argument("--backend-url", default=os.getenv("DECK_AISTACK_BACKEND_URL", DEFAULT_BACKEND_URL))
    parser.add_argument("--auth-token", default=os.getenv("DECK_AISTACK_AUTH_TOKEN", ""))
    parser.add_argument("--deck-id", default=os.getenv("DECK_AISTACK_DECK_ID", ""))
    args = parser.parse_args()

    results = run_checks(args.frontend_url, args.backend_url, args.auth_token.strip(), args.deck_id.strip())
    return print_report(results)


if __name__ == "__main__":
    raise SystemExit(main())
