#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise SystemExit("Missing dependency: PyYAML. Install backend requirements first.") from exc


REQUIRED_ARCHETYPE_FIELDS = (
    "id",
    "slug",
    "title",
    "description",
    "deck_types",
    "tags",
    "sequence",
    "body_md",
    "narrative_role",
    "required_inputs",
    "evidence_hierarchy",
    "generation_rules",
    "critique_rules",
    "rewrite_modes",
    "visual_guidance",
    "llm_contract",
    "render_contract",
    "quality_rubric",
    "output_contract",
    "validation_rules",
    "frontend_render_hints",
)

REQUIRED_MODULE_IDS = {
    "deck_types",
    "narrative_flows",
    "render_schema_rules",
    "writing_rules",
    "quality_rubrics",
    "hallucination_constraints",
    "retrieval_routing",
    "deck_recipes",
    "diagnostics",
    "generation_contracts",
    "examples",
    "eval_cases",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def validate(base: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = base / "manifest.yaml"
    compiled_dir = base / "compiled_json"
    index_path = compiled_dir / "archetypes.index.json"

    if not manifest_path.exists():
        return [f"Missing manifest: {manifest_path}"]
    if not index_path.exists():
        return [f"Missing compiled index: {index_path}"]

    manifest = _load_yaml(manifest_path)
    index = _load_json(index_path)
    manifest_version = str(manifest.get("version") or "").strip()
    index_version = str(index.get("version") or "").strip()
    if not manifest_version:
        _add_error(errors, "manifest.yaml is missing version.")
    if index_version != manifest_version:
        _add_error(errors, f"Compiled version {index_version!r} does not match manifest version {manifest_version!r}.")

    manifest_modules = manifest.get("knowledge_modules")
    if not isinstance(manifest_modules, list):
        _add_error(errors, "manifest.yaml knowledge_modules must be a list.")
        manifest_modules = []

    module_ids: set[str] = set()
    for module in manifest_modules:
        if not isinstance(module, dict):
            _add_error(errors, "manifest.yaml contains a non-object knowledge module entry.")
            continue
        module_id = str(module.get("id") or "").strip()
        module_path = str(module.get("path") or "").strip()
        if not module_id or not module_path:
            _add_error(errors, f"Knowledge module is missing id/path: {module!r}")
            continue
        if module_id in module_ids:
            _add_error(errors, f"Duplicate knowledge module id: {module_id}")
        module_ids.add(module_id)
        source_path = base / module_path
        compiled_path = compiled_dir / "modules" / f"{module_id}.json"
        if not source_path.exists():
            _add_error(errors, f"Missing module source file: {source_path}")
        else:
            payload = _load_yaml(source_path)
            if not payload:
                _add_error(errors, f"Module source is empty or invalid: {source_path}")
        if not compiled_path.exists():
            _add_error(errors, f"Missing compiled module file: {compiled_path}")
        else:
            compiled_module = _load_json(compiled_path)
            if compiled_module.get("id") != module_id:
                _add_error(errors, f"Compiled module id mismatch in {compiled_path}")

    missing_required_modules = sorted(REQUIRED_MODULE_IDS - module_ids)
    if missing_required_modules:
        _add_error(errors, f"Missing required knowledge modules: {', '.join(missing_required_modules)}")

    compiled_modules = index.get("knowledge_modules")
    if not isinstance(compiled_modules, dict):
        _add_error(errors, "Compiled index knowledge_modules must be an object.")
        compiled_modules = {}
    for module_id in module_ids:
        if module_id not in compiled_modules:
            _add_error(errors, f"Compiled index does not include manifest module: {module_id}")

    archetypes = index.get("archetypes")
    if not isinstance(archetypes, list) or not archetypes:
        _add_error(errors, "Compiled index archetypes must be a non-empty list.")
        archetypes = []
    if index.get("archetype_count") != len(archetypes):
        _add_error(errors, "Compiled index archetype_count does not match archetypes length.")

    seen_slugs: set[str] = set()
    seen_ids: set[str] = set()
    relationship_graph = index.get("relationship_graph") if isinstance(index.get("relationship_graph"), dict) else {}
    for archetype in archetypes:
        if not isinstance(archetype, dict):
            _add_error(errors, "Compiled index contains a non-object archetype.")
            continue
        slug = str(archetype.get("slug") or "").strip()
        archetype_id = str(archetype.get("id") or "").strip()
        if not slug:
            _add_error(errors, "Archetype is missing slug.")
            continue
        if slug in seen_slugs:
            _add_error(errors, f"Duplicate archetype slug: {slug}")
        seen_slugs.add(slug)
        if archetype_id in seen_ids:
            _add_error(errors, f"Duplicate archetype id: {archetype_id}")
        seen_ids.add(archetype_id)
        detail_path = compiled_dir / "archetypes" / f"{slug}.json"
        if not detail_path.exists():
            _add_error(errors, f"Missing compiled archetype detail: {detail_path}")
        else:
            detail = _load_json(detail_path)
            if detail.get("slug") != slug:
                _add_error(errors, f"Compiled archetype detail slug mismatch: {detail_path}")
        missing_fields = [
            field
            for field in REQUIRED_ARCHETYPE_FIELDS
            if field not in archetype or archetype.get(field) in (None, "", [], {})
        ]
        if missing_fields:
            _add_error(errors, f"Archetype {slug} missing fields: {', '.join(missing_fields)}")
        render_contract = archetype.get("render_contract") if isinstance(archetype.get("render_contract"), dict) else {}
        if render_contract.get("schema_version") != "smart-deck-render-schema.v1":
            _add_error(errors, f"Archetype {slug} render_contract.schema_version is not smart-deck-render-schema.v1.")
        if slug not in relationship_graph:
            _add_error(errors, f"Relationship graph missing archetype slug: {slug}")

    runtime_contract = index.get("runtime_contract") if isinstance(index.get("runtime_contract"), dict) else {}
    if "render_schema_json" not in str(runtime_contract.get("renderer_rule") or ""):
        _add_error(errors, "Runtime contract renderer_rule must require render_schema_json.")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base",
        default=None,
        help="Deck archetype knowledge base folder.",
    )
    args = parser.parse_args()
    if args.base:
        base = Path(args.base).resolve()
    else:
        backend_root = Path(__file__).resolve().parents[1]
        base = backend_root / "llm_knowledge" / "deck_archetype_knowledge"
    errors = validate(base)
    if errors:
        print("LLM knowledge validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    index = _load_json(base / "compiled_json" / "archetypes.index.json")
    print(
        "LLM knowledge validation passed: "
        f"version={index.get('version')} archetypes={index.get('archetype_count')} "
        f"modules={len(index.get('knowledge_modules') or {})}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
