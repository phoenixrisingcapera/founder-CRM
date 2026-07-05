from __future__ import annotations

from pathlib import Path

FORBIDDEN_PATTERNS = {
    "/api/v1": "DeckAiStack production product routes must not use /api/v1.",
    "/api/products/dididecks": "Current production product prefix is /api/products/deck-aistack-codes.",
    "src/lib/components/dididecks": "Frontend component paths do not belong in backend canonical docs.",
    "UploadDropzonePanel.svelte": "Missing frontend planning component must not be backend canonical.",
    "save-confirmation.mapper.ts": "Frontend save-confirmation mapper claim must not be backend canonical.",
    "/decks/[deckId]/shell": "Shell route is not a backend production canonical.",
    "/home/phoenix/Documents/dddecks-ai/": "Absolute workstation paths are not production canonicals.",
}

REQUIRED_FILES = {
    "docs/CANONICAL_PRODUCTION_CONTRACT.md",
    "scripts/verify_production_contract.py",
    "app/main.py",
}

SCAN_DIRS = ["app", "scripts"]
SCAN_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yml", ".yaml"}
ALLOWLIST = {
    "docs/CANONICAL_PRODUCTION_CONTRACT.md",
    "scripts/verify_canonical_backend_contract.py",
}
EXCLUDE_PATHS = {
    "scripts/verify_production_contract.py",
    "scripts/verify_production_workflow_contract.py",
    "app/services/guardrail_client.py",
    "app/ai/openrouter_provider.py",
}


def iter_text_files() -> list[Path]:
    paths: list[Path] = []
    for root in SCAN_DIRS:
        base = Path(root)
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_dir():
                continue
            if path.suffix not in SCAN_SUFFIXES:
                continue
            normalized = path.as_posix()
            if any(normalized.startswith(prefix) for prefix in EXCLUDE_PATHS):
                continue
            if "__pycache__" in normalized or ".pytest_cache" in normalized:
                continue
            paths.append(path)
    return paths


def main() -> int:
    failures: list[str] = []

    for required in sorted(REQUIRED_FILES):
        if not Path(required).exists():
            failures.append(f"Missing required canonical backend file: {required}")

    for path in iter_text_files():
        normalized = path.as_posix()
        if normalized in ALLOWLIST:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for pattern, message in FORBIDDEN_PATTERNS.items():
            if pattern in content:
                failures.append(f"{normalized}: {message}")

    if failures:
        print("Canonical backend contract verification FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Canonical backend contract verification PASSED")
    print("Production prefix is /api/products/deck-aistack-codes")
    print("No stale /api/v1, dididecks product-prefix, shell-route, or frontend component canonical claims found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
