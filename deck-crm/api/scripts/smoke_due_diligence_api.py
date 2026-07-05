from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SmokeConfig:
    base_url: str
    deck_id: str
    token: str
    audience: str
    run_audience: str
    timeout_seconds: float


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _json_request(config: SmokeConfig, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    if payload is None:
        body = None
    else:
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        f"{config.base_url.rstrip('/')}{path}",
        method=method,
        headers={
            "Authorization": f"Bearer {config.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "deck-aistack-due-diligence-smoke/1.0",
        },
        data=body,
    )

    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            payload_bytes = response.read().decode("utf-8")
            return response.status, json.loads(payload_bytes) if payload_bytes else {}
    except urllib.error.HTTPError as exc:
        payload_text = exc.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(payload_text) if payload_text else {}
        except json.JSONDecodeError:
            details = {"raw": payload_text}
        raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc.reason}") from exc


def _field(payload: dict[str, Any], *possible_keys: str) -> Any:
    for key in possible_keys:
        if key in payload:
            return payload[key]
    raise RuntimeError(f"Missing any of keys: {', '.join(possible_keys)} in payload={payload}")


def _require_fields_with_aliases(payload: dict[str, Any], fields: list[list[str]], context: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for aliases in fields:
        value = _field(payload, *aliases)
        values[aliases[0]] = value
    return values


def _require_list(payload: dict[str, Any], key: str, context: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise RuntimeError(f"{context} response has invalid {key!r}: {type(value).__name__}")
    return value


def run_smoke(config: SmokeConfig) -> None:
    deck_path = f"/api/products/deck-aistack-codes/decks/{config.deck_id}"

    get_path = f"{deck_path}/due-diligence?audience={_url_safe(config.audience)}"
    get_code, get_payload = _json_request(config, "GET", get_path)
    if get_code != 200:
        raise RuntimeError(f"Unexpected GET status: {get_code}")
    get_fields = _require_fields_with_aliases(
        get_payload,
        [
            ["deck_id", "deckId"],
            ["run_id", "runId"],
            ["status"],
            ["selected_audience", "selectedAudience"],
            ["summary"],
            ["domains"],
            ["claims"],
            ["audience_fit", "audienceFit"],
            ["ic_memo", "icMemo"],
            ["lp_view", "lpView"],
            ["risk_register", "riskRegister"],
        ],
        "GET /due-diligence",
    )
    _require_list(get_payload, "domains", "GET /due-diligence")
    print(f"ok: GET due diligence workspace loaded (selectedAudience={get_fields['selected_audience']})")

    post_path = f"{deck_path}/due-diligence/run"
    post_code, post_payload = _json_request(
        config,
        "POST",
        post_path,
        payload={"audience": config.run_audience, "run_mode": "full_review"},
    )
    if post_code != 200:
        raise RuntimeError(f"Unexpected POST status: {post_code}")
    post_fields = _require_fields_with_aliases(
        post_payload,
        [
            ["deck_id", "deckId"],
            ["status"],
            ["selected_audience", "selectedAudience"],
            ["summary"],
            ["domains"],
            ["claims"],
            ["audience_fit", "audienceFit"],
        ],
        "POST /due-diligence/run",
    )
    if post_fields["selected_audience"] != config.run_audience:
        raise RuntimeError(
            f"POST selected_audience mismatch: expected {config.run_audience}, got {post_fields['selected_audience']}"
        )
    print(f"ok: POST due diligence run completed (selectedAudience={post_fields['selected_audience']}, status={post_fields['status']})")

    refresh_code, refresh_payload = _json_request(
        config,
        "GET",
        f"{deck_path}/due-diligence?audience={_url_safe(config.run_audience)}",
    )
    if refresh_code != 200:
        raise RuntimeError(f"Unexpected POST-refresh GET status: {refresh_code}")
    refresh_fields = _require_fields_with_aliases(
        refresh_payload,
        [["selected_audience", "selectedAudience"]],
        "follow-up GET",
    )
    print(f"ok: audience-switch GET persisted run result ({refresh_fields['selected_audience']})")


def _url_safe(value: str) -> str:
    return urllib.parse.quote(value or "seed_vc")


def _parse_args() -> SmokeConfig:
    parser = argparse.ArgumentParser(
        description="Smoke test Due Diligence GET/POST endpoints against a real backend."
    )
    parser.add_argument("--base-url", default=_env("DECK_AISTACK_SMOKE_BASE_URL"), required=False)
    parser.add_argument("--deck-id", default=_env("DECK_AISTACK_SMOKE_DECK_ID"), required=False)
    parser.add_argument("--token", default=_env("DECK_AISTACK_SMOKE_TOKEN"), required=False)
    parser.add_argument(
        "--audience",
        default=_env("DECK_AISTACK_SMOKE_DUE_AUDIENCE") or "seed_vc",
        help="Audience for initial GET check (default: seed_vc).",
    )
    parser.add_argument(
        "--run-audience",
        default=_env("DECK_AISTACK_SMOKE_DUE_RUN_AUDIENCE") or "series_a_vc",
        help="Audience for POST /run and follow-up GET (default: series_a_vc).",
    )
    parser.add_argument("--timeout-seconds", type=float, default=float(_env("DECK_AISTACK_SMOKE_TIMEOUT") or "30"))

    args = parser.parse_args()
    missing = [
        name
        for name, value in {
            "--base-url/DECK_AISTACK_SMOKE_BASE_URL": args.base_url,
            "--deck-id/DECK_AISTACK_SMOKE_DECK_ID": args.deck_id,
            "--token/DECK_AISTACK_SMOKE_TOKEN": args.token,
        }.items()
        if not value
    ]
    if missing:
        parser.error("Missing required values: " + ", ".join(missing))

    return SmokeConfig(
        base_url=str(args.base_url),
        deck_id=str(args.deck_id),
        token=str(args.token),
        audience=str(args.audience),
        run_audience=str(args.run_audience),
        timeout_seconds=float(args.timeout_seconds),
    )


def main() -> int:
    try:
        config = _parse_args()
        run_smoke(config)
    except RuntimeError as exc:
        print(f"failed: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("canceled", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
