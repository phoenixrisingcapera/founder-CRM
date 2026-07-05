from __future__ import annotations

from pathlib import Path
import sys

from fastapi.routing import APIRoute

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app

SMART_DECK_PATH = "/api/products/deck-aistack-codes/decks/{deck_id}/smart-deck"
BRAND_STATUS_PATH = "/api/products/deck-aistack-codes/decks/{deck_id}/brand/status"

EXPECTED_PATHS = {
    "/api/health",
    "/api/auth/sign-in",
    "/api/auth/me",
    "/api/products/deck-aistack-codes/welcome-state",
    "/api/products/deck-aistack-codes/workspace-summary",
    "/api/products/deck-aistack-codes/decks",
    "/api/products/deck-aistack-codes/decks/upload",
    "/api/products/deck-aistack-codes/decks/upload-session",
    "/api/settings/workspace/ai-provider",
    "/api/products/deck-aistack-codes/decks/{deck_id}/status",
    "/api/products/deck-aistack-codes/decks/{deck_id}/workflow-state",
    "/api/products/deck-aistack-codes/decks/{deck_id}/processing",
    "/api/products/deck-aistack-codes/decks/{deck_id}/workflows/source-extraction",
    "/api/workflow-jobs/{job_id}",
    "/api/products/deck-aistack-codes/decks/{deck_id}/structure",
    "/api/products/deck-aistack-codes/decks/{deck_id}/brand/extract",
    BRAND_STATUS_PATH,
    "/api/products/deck-aistack-codes/decks/{deck_id}/brand-profile",
    "/api/products/deck-aistack-codes/decks/{deck_id}/brand-assets/{asset_id}",
    "/api/products/deck-aistack-codes/decks/{deck_id}/editable-fields",
    "/api/products/deck-aistack-codes/decks/{deck_id}/changes/preview",
    "/api/products/deck-aistack-codes/decks/{deck_id}/changes/apply",
    SMART_DECK_PATH,
    "/api/products/deck-aistack-codes/decks/{deck_id}/smart-deck/generation-jobs",
    "/api/products/deck-aistack-codes/decks/{deck_id}/smart-deck/generation-jobs/{job_id}",
}

REQUIRED_RUNTIME_FILES = {
    "scripts/start_railway.py",
    "railway.toml",
}


def _registered_paths() -> set[str]:
    return {route.path for route in app.routes if isinstance(route, APIRoute)}


def _load_gitignore_lines() -> list[str]:
    with open(".gitignore", "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle.readlines() if line.strip() and not line.lstrip().startswith("#")]


def _verify_gitignore_contract() -> None:
    lines = _load_gitignore_lines()
    blocked = [line for line in lines if line in {"tests/", "docs/"}]
    if blocked:
        blocked_str = ", ".join(sorted(blocked))
        raise RuntimeError(f"Blocked tracked paths in .gitignore: {blocked_str}")


def _verify_runtime_files() -> list[str]:
    return [path for path in sorted(REQUIRED_RUNTIME_FILES) if not Path(path).exists()]


def _verify_railway_start_command() -> str | None:
    railway = Path("railway.toml")
    if not railway.exists():
        return "railway.toml is missing"
    content = railway.read_text(encoding="utf-8")
    if "python scripts/start_railway.py" not in content:
        return "railway.toml must use python scripts/start_railway.py as the start command"
    return None


def main() -> int:
    failures: list[str] = []

    registered_paths = _registered_paths()
    missing_routes = sorted(EXPECTED_PATHS - registered_paths)
    if missing_routes:
        failures.append(f"Missing production routes: {missing_routes}")

    api_v1_routes = [path for path in sorted(registered_paths) if path.startswith("/api/v1")]
    if api_v1_routes:
        failures.append(f"Routes still use /api/v1: {api_v1_routes}")

    if not any(path.startswith("/api/products/deck-aistack-codes") for path in registered_paths):
        failures.append("No /api/products/deck-aistack-codes route path found.")

    if SMART_DECK_PATH not in registered_paths:
        failures.append("Product Smart Deck route missing under production prefix.")

    if BRAND_STATUS_PATH not in registered_paths:
        failures.append("Brand extraction status route missing under production prefix.")

    missing_runtime_files = _verify_runtime_files()
    if missing_runtime_files:
        failures.append(f"Missing Railway runtime files: {missing_runtime_files}")

    railway_failure = _verify_railway_start_command()
    if railway_failure:
        failures.append(railway_failure)

    try:
        _verify_gitignore_contract()
    except RuntimeError as exc:
        failures.append(str(exc))

    if failures:
        print("Production contract checks FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Production contract checks PASSED")
    print(f"Registered production route count: {len(registered_paths)}")
    print("Tracked gitignore policy includes docs/ and tests/ as commitable paths.")
    print("Railway start command present: python scripts/start_railway.py")
    print(f"Smart Deck route present: {SMART_DECK_PATH in registered_paths}")
    print(f"Brand status route present: {BRAND_STATUS_PATH in registered_paths}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
