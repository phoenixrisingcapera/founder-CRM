from __future__ import annotations

from pathlib import Path
import sys

from fastapi.routing import APIRoute

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app

PRODUCT_PREFIX = "/api/products/deck-aistack-codes"

REQUIRED_WORKFLOW_PATHS = {
    "/api/health": "health",
    "/api/auth/sign-in": "sign_in",
    "/api/auth/me": "current_user",
    "/api/settings/workspace/ai-provider": "workspace_ai_provider",
    f"{PRODUCT_PREFIX}/workspace-summary": "workspace_summary",
    f"{PRODUCT_PREFIX}/decks": "deck_list_create",
    f"{PRODUCT_PREFIX}/decks/upload": "upload",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/status": "status",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/workflow-state": "workflow_state",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/processing": "processing_compatibility",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/workflows/source-extraction": "source_extraction_workflow",
    f"/api/workflow-jobs/{{job_id}}": "workflow_job_detail",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/structure": "structure",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/smart-deck": "smart_deck",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/brand-profile": "brand_profile",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/soft-delete": "soft_delete",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/due-diligence": "due_diligence",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/editable-fields": "editable_fields",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/changes/preview": "changes_preview",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/changes/apply": "changes_apply",
    f"{PRODUCT_PREFIX}/decks/{{deck_id}}/exports": "exports",
}

OPTIONAL_WORKFLOW_PATHS = {
    # The production workflow routes that used to be optional are now required
    # above because main already registers them and the app depends on them.
}

FORBIDDEN_SOURCE_PATTERNS = {
    "/api/v1": "DeckAiStack production routes must not use /api/v1.",
    "/api/products/dididecks": "This production repo currently uses /api/products/deck-aistack-codes, not /dididecks.",
}

SCAN_DIRS = ["app/api"]
SCAN_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yml", ".yaml"}
ALLOWLIST = {
    "scripts/verify_production_workflow_contract.py",
    "docs/CANONICAL_PRODUCTION_CONTRACT.md",
}


def registered_routes() -> dict[str, set[str]]:
    routes: dict[str, set[str]] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        routes.setdefault(route.path, set()).update(route.methods or set())
    return routes


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_DIRS:
        base = Path(root)
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_dir():
                continue
            normalized = path.as_posix()
            if "__pycache__" in normalized or ".pytest_cache" in normalized:
                continue
            if path.suffix in SCAN_SUFFIXES:
                files.append(path)
    return files


def scan_forbidden_patterns() -> list[str]:
    failures: list[str] = []
    for path in iter_text_files():
        normalized = path.as_posix()
        if normalized in ALLOWLIST:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for pattern, message in FORBIDDEN_SOURCE_PATTERNS.items():
            if pattern in content:
                failures.append(f"{normalized}: {message}")
    return failures


def main() -> int:
    routes = registered_routes()
    blockers: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    for path, name in REQUIRED_WORKFLOW_PATHS.items():
        if path not in routes:
            blockers.append(f"Missing required workflow route [{name}]: {path}")

    for path, name in OPTIONAL_WORKFLOW_PATHS.items():
        if path not in routes:
            warnings.append(f"Optional workflow route not registered yet [{name}]: {path}")

    upload_methods = routes.get(f"{PRODUCT_PREFIX}/decks/upload", set())
    if "POST" not in upload_methods:
        blockers.append("Upload route exists but does not expose POST.")

    deck_collection_methods = routes.get(f"{PRODUCT_PREFIX}/decks", set())
    if not ({"GET", "POST"} & deck_collection_methods):
        blockers.append("Deck collection route must expose GET and/or POST for production workspace flow.")

    for route_path in routes:
        if route_path.startswith("/api/v1"):
            blockers.append(f"Registered route still uses /api/v1: {route_path}")

    blockers.extend(scan_forbidden_patterns())

    if not any(path.startswith(PRODUCT_PREFIX) for path in routes):
        blockers.append(f"No product-prefixed routes registered under {PRODUCT_PREFIX}.")

    if not blockers:
        info.append(f"Registered production workflow routes: {len([p for p in routes if p.startswith(PRODUCT_PREFIX)])}")
        info.append("Required workflow contract routes are registered.")

    print("Backend Production Workflow Contract Report")
    print("status:", "NOT_READY" if blockers else "PARTIAL" if warnings else "READY")
    print("\nBlockers:")
    print("\n".join(f"- {item}" for item in blockers) if blockers else "- none")
    print("\nWarnings:")
    print("\n".join(f"- {item}" for item in warnings) if warnings else "- none")
    print("\nInfo:")
    print("\n".join(f"- {item}" for item in info) if info else "- none")

    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
