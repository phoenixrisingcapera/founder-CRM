from __future__ import annotations

import os
import sys
from urllib.parse import urlencode

import httpx


def main() -> int:
    api_url = os.getenv("DECK_API_URL", "").rstrip("/")
    token = os.getenv("DECK_ADMIN_BEARER_TOKEN", "").strip()

    if not api_url:
        print("DECK_API_URL is required.")
        return 2
    if not token:
        print("DECK_ADMIN_BEARER_TOKEN is required.")
        return 2

    params = urlencode({"limit": 1})
    url = f"{api_url}/api/admin/failure-tickets?{params}"
    headers = {"authorization": f"Bearer {token}"}

    try:
        response = httpx.get(url, headers=headers, timeout=20)
    except httpx.HTTPError as exc:
        print(f"request_failed: {exc}")
        return 1

    print(f"status={response.status_code}")
    if response.status_code >= 400:
        print(response.text)
        return 1

    try:
        payload = response.json()
    except ValueError:
        print("invalid_json")
        return 1

    tickets = payload.get("tickets") or payload.get("items") or payload.get("results") or []
    print(f"tickets={len(tickets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
