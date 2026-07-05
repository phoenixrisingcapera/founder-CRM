from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SmokeConfig:
    base_url: str
    deck_id: str
    token: str
    run_extraction: bool
    check_asset_url: bool
    timeout_seconds: float


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _json_request(config: SmokeConfig, method: str, path: str) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        f"{config.base_url.rstrip('/')}{path}",
        method=method,
        headers={
            "Authorization": f"Bearer {config.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "deck-extraction-smoke/1.0",
        },
        data=b"{}" if method in {"POST", "PUT", "PATCH"} else None,
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            details = {"raw": payload}
        raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc.reason}") from exc


def _asset_request(config: SmokeConfig, asset_url: str) -> int:
    request = urllib.request.Request(
        f"{config.base_url.rstrip('/')}{asset_url}",
        method="GET",
        headers={
            "Authorization": f"Bearer {config.token}",
            "User-Agent": "deck-extraction-smoke/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            response.read(64)
            return response.status
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GET {asset_url} failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GET {asset_url} failed: {exc.reason}") from exc


def _require_mapping(payload: dict[str, Any], key: str, path: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} response is missing object field {key!r}: {payload}")
    return value


def _require_list(payload: dict[str, Any], key: str, path: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise RuntimeError(f"{path} response is missing list field {key!r}: {payload}")
    return value


def _first_asset_url(structure: dict[str, Any]) -> str | None:
    slides = structure.get("slides")
    if not isinstance(slides, list):
        return None
    for slide in slides:
        if not isinstance(slide, dict):
            continue
        assets = slide.get("assets")
        if not isinstance(assets, list):
            continue
        for asset in assets:
            if isinstance(asset, dict) and isinstance(asset.get("assetUrl"), str):
                return asset["assetUrl"]
    return None


def run_smoke(config: SmokeConfig) -> None:
    deck_path = f"/api/products/deck-aistack-codes/decks/{config.deck_id}"

    status_code, status_payload = _json_request(config, "GET", f"{deck_path}/status")
    if status_code != 200:
        raise RuntimeError(f"Unexpected status response code: {status_code}")
    print(f"ok: status loaded ({status_payload.get('status') or status_payload.get('deckStatus') or 'unknown'})")

    if config.run_extraction:
        extraction_code, extraction_payload = _json_request(config, "POST", f"{deck_path}/extract-structure")
        if extraction_code != 200 or extraction_payload.get("ok") is not True:
            raise RuntimeError(f"Extraction response was not successful: {extraction_payload}")
        _require_mapping(extraction_payload, "structure", "extract-structure")
        print("ok: extract-structure completed")

    structure_code, structure_payload = _json_request(config, "GET", f"{deck_path}/structure")
    if structure_code != 200:
        raise RuntimeError(f"Unexpected structure response code: {structure_code}")
    slides = _require_list(structure_payload, "slides", "structure")
    if not slides:
        raise RuntimeError("structure response has no slides")
    print(f"ok: structure loaded ({len(slides)} slides)")

    artifacts_code, artifacts_payload = _json_request(config, "GET", f"{deck_path}/artifacts")
    if artifacts_code != 200:
        raise RuntimeError(f"Unexpected artifacts response code: {artifacts_code}")
    artifacts = _require_list(artifacts_payload, "artifacts", "artifacts")
    print(f"ok: artifacts loaded ({len(artifacts)} artifacts)")

    if config.check_asset_url:
        asset_url = _first_asset_url(structure_payload)
        if not asset_url:
            raise RuntimeError("structure response did not include any assetUrl values")
        asset_code = _asset_request(config, asset_url)
        if asset_code != 200:
            raise RuntimeError(f"Unexpected asset response code: {asset_code}")
        print("ok: first persisted asset URL loaded")


def _parse_args() -> SmokeConfig:
    parser = argparse.ArgumentParser(
        description="Smoke test persisted deck extraction API endpoints against a real backend."
    )
    parser.add_argument("--base-url", default=_env("DECK_AISTACK_SMOKE_BASE_URL"))
    parser.add_argument("--deck-id", default=_env("DECK_AISTACK_SMOKE_DECK_ID"))
    parser.add_argument("--token", default=_env("DECK_AISTACK_SMOKE_TOKEN"))
    parser.add_argument(
        "--run-extraction",
        action="store_true",
        default=_env("DECK_AISTACK_SMOKE_RUN_EXTRACTION") == "1",
        help="POST extract-structure before reading persisted structure/artifacts.",
    )
    parser.add_argument(
        "--check-asset-url",
        action="store_true",
        default=_env("DECK_AISTACK_SMOKE_CHECK_ASSET_URL") == "1",
        help="Fetch the first assetUrl returned by the structure endpoint.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=float(_env("DECK_AISTACK_SMOKE_TIMEOUT") or "30"))
    args = parser.parse_args()

    missing = [
        name
        for name, value in {
            "--base-url or DECK_AISTACK_SMOKE_BASE_URL": args.base_url,
            "--deck-id or DECK_AISTACK_SMOKE_DECK_ID": args.deck_id,
            "--token or DECK_AISTACK_SMOKE_TOKEN": args.token,
        }.items()
        if not value
    ]
    if missing:
        parser.error("Missing required values: " + ", ".join(missing))

    return SmokeConfig(
        base_url=str(args.base_url).rstrip("/"),
        deck_id=str(args.deck_id),
        token=str(args.token),
        run_extraction=bool(args.run_extraction),
        check_asset_url=bool(args.check_asset_url),
        timeout_seconds=float(args.timeout_seconds),
    )


def main() -> int:
    config = _parse_args()
    try:
        run_smoke(config)
    except RuntimeError as exc:
        print(f"failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
