#!/usr/bin/env python3
"""Verify the DeckAiStack LLM knowledge runtime contract.

This is a lightweight production-readiness check. It confirms that the backend can
load the knowledge services and that the admin routes needed by the frontend and
operators are registered.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_ROUTES = {
    "/api/admin/llm-knowledge/health": {"GET"},
    "/api/admin/llm-knowledge/full-health": {"GET"},
    "/api/admin/llm-knowledge/tasks": {"GET"},
    "/api/admin/llm-knowledge/reload": {"POST"},
}

REQUIRED_PACKAGES = {
    "deck_archetypes",
    "due_diligence",
    "architecture_runtime",
    "market_research",
}

REQUIRED_TASKS = {
    "slide_classification",
    "block_classification",
    "market_verification",
}


def _registered_routes() -> dict[str, set[str]]:
    from app.main import app

    routes: dict[str, set[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods:
            continue
        routes[path] = set(methods)
    return routes


def _check_routes(errors: list[str]) -> None:
    routes = _registered_routes()
    for path, methods in REQUIRED_ROUTES.items():
        actual_methods = routes.get(path)
        if actual_methods is None:
            errors.append(f"Missing route: {path}")
            continue
        missing = methods - actual_methods
        if missing:
            errors.append(f"Route {path} missing methods: {sorted(missing)}")


def _check_health_shape(errors: list[str], warnings: list[str]) -> None:
    from app.services.llm_knowledge_service import get_llm_knowledge_health

    health = get_llm_knowledge_health()
    packages = health.get("packages") if isinstance(health.get("packages"), dict) else {}
    tasks = health.get("tasks") if isinstance(health.get("tasks"), dict) else {}

    missing_packages = sorted(REQUIRED_PACKAGES - set(packages.keys()))
    if missing_packages:
        errors.append(f"LLM health missing packages: {missing_packages}")

    missing_tasks = sorted(REQUIRED_TASKS - set(tasks.keys()))
    if missing_tasks:
        errors.append(f"LLM health missing tasks: {missing_tasks}")

    for package_name in REQUIRED_PACKAGES & set(packages.keys()):
        package = packages[package_name]
        if not isinstance(package, dict):
            errors.append(f"LLM package {package_name} is not an object")
            continue
        if "ready" not in package:
            warnings.append(f"LLM package {package_name} has no ready flag")
        if "requiredModules" not in package:
            warnings.append(f"LLM package {package_name} has no requiredModules block")

    if health.get("status") != "ready":
        warnings.append(f"LLM knowledge status is {health.get('status')!r}; inspect missing modules before production.")


def _check_task_contracts(errors: list[str]) -> None:
    from app.services.llm_knowledge_service import get_llm_knowledge_task_contracts

    contracts = get_llm_knowledge_task_contracts()
    tasks = contracts.get("tasks") if isinstance(contracts.get("tasks"), dict) else {}
    for task_name in REQUIRED_TASKS:
        task = tasks.get(task_name)
        if not isinstance(task, dict):
            errors.append(f"Task contract missing: {task_name}")
            continue
        for key in ("knowledgePack", "requiredOutputs", "artifactMetadata"):
            if key not in task:
                errors.append(f"Task contract {task_name} missing {key}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    _check_routes(errors)
    _check_health_shape(errors, warnings)
    _check_task_contracts(errors)

    if errors:
        print("LLM knowledge contract: FAILED")
        for error in errors:
            print(f"- ERROR: {error}")
        for warning in warnings:
            print(f"- WARN: {warning}")
        return 1

    print("LLM knowledge contract: OK")
    for warning in warnings:
        print(f"- WARN: {warning}")
    print("Verified admin routes, package health shape, task contracts, and reload support.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
