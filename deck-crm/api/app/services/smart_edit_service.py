from __future__ import annotations

import re

from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.agents.smart_edit_agent import run as smart_edit_run
from app.ai.architecture_runtime_context import build_architecture_runtime_context
from app.core.security import generate_id
from app.db.models import Deck, DeckLlmArtifact, DeckSlide, DeckSlideBlock, SmartEditRun, SmartEditSuggestion
from app.ai.slide_archetypes_context import build_slide_archetype_context
from app.services.agent_telemetry_service import record_agent_event
from app.services.critique_service import build_critique_decision
from app.services.llm_artifact_persistence_service import persist_canonical_llm_artifact
from app.services.llm_knowledge_service import build_llm_knowledge_metadata
from app.services.smart_deck_llm_service import _resolve_claude_config
from app.services.source_fact_service import classify_source_fact, summarize_fact_types, summarize_safety_flags


ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
MAX_SUGGESTION_TEXT_LENGTH = 4000
SMART_EDIT_ARTIFACT_SCHEMA_VERSION = "smart-edit-artifacts.v1"
SMART_EDIT_FACT_MAX_LENGTH = 320


def _safe_text(value: object, *, fallback: str = "") -> str:
    text = str(value if value is not None else fallback).strip()
    return "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)[:MAX_SUGGESTION_TEXT_LENGTH]


def _normalize_suggestion_payload(payload: dict[str, object], *, original_text: str) -> dict[str, str]:
    suggested_text = _safe_text(payload.get("suggested_text"), fallback=original_text)
    reason = _safe_text(payload.get("reason"), fallback="Suggested by Smart Edit.")
    risk_level = _safe_text(payload.get("risk_level"), fallback="medium").lower()
    if risk_level not in ALLOWED_RISK_LEVELS:
        risk_level = "medium"
    return {
        "original_text": _safe_text(payload.get("original_text"), fallback=original_text),
        "suggested_text": suggested_text or original_text,
        "reason": reason or "Suggested by Smart Edit.",
        "risk_level": risk_level,
    }


def _normalise_fact_text(value: object, *, limit: int = SMART_EDIT_FACT_MAX_LENGTH) -> str:
    text = str(value if value is not None else "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:limit].strip()


def _fact_candidates_from_text(text: str | None) -> list[str]:
    normalized = _normalise_fact_text(text, limit=4000)
    if not normalized:
        return []
    parts = [
        part.strip(" -:\t")
        for part in re.split(r"(?<=[.!?])\s+|\n+|[•·]\s*", normalized)
        if part.strip(" -:\t")
    ]
    if len(parts) <= 1:
        parts = [
            part.strip(" -:\t")
            for part in re.split(r"\s{2,}|;\s+", normalized)
            if part.strip(" -:\t")
        ]
    return [_normalise_fact_text(part) for part in parts if len(part) >= 8]


def _append_source_fact(
    facts: list[dict],
    seen: set[str],
    *,
    source_type: str,
    source_id: str,
    field: str,
    text: object,
    confidence: str,
    scope: str,
) -> None:
    fact_text = _normalise_fact_text(text)
    if not fact_text:
        return
    key = f"{source_type}:{source_id}:{field}:{fact_text.lower()}"
    if key in seen:
        return
    seen.add(key)
    classification = classify_source_fact(
        text=fact_text,
        source_type=source_type,
        field=field,
        confidence=confidence,
    )
    facts.append(
        {
            "id": f"fact_{len(facts) + 1}",
            "sourceType": source_type,
            "sourceId": source_id,
            "field": field,
            "text": fact_text,
            "confidence": confidence,
            "scope": scope,
            **classification,
        }
    )


def _build_smart_edit_source_fact_package(
    *,
    deck: Deck,
    selected_slide: DeckSlide | None,
    selected_block: DeckSlideBlock | None,
    instruction: str,
    audience_type: str,
) -> dict:
    facts: list[dict] = []
    seen: set[str] = set()
    _append_source_fact(facts, seen, source_type="deck_metadata", source_id=deck.id, field="title", text=deck.title, confidence="high", scope="deck")
    _append_source_fact(facts, seen, source_type="deck_metadata", source_id=deck.id, field="audience", text=deck.audience, confidence="high", scope="deck")
    _append_source_fact(facts, seen, source_type="deck_metadata", source_id=deck.id, field="purpose", text=deck.purpose, confidence="high", scope="deck")
    _append_source_fact(facts, seen, source_type="smart_edit_instruction", source_id=deck.id, field="instruction", text=instruction, confidence="high", scope="edit")
    _append_source_fact(facts, seen, source_type="smart_edit_instruction", source_id=deck.id, field="audience_type", text=audience_type, confidence="high", scope="edit")

    if selected_slide is not None:
        _append_source_fact(facts, seen, source_type="source_slide", source_id=selected_slide.id, field="title", text=selected_slide.title, confidence="high", scope="slide")
        _append_source_fact(facts, seen, source_type="source_slide", source_id=selected_slide.id, field="role", text=selected_slide.role, confidence="medium", scope="slide")
        for candidate in _fact_candidates_from_text(selected_slide.raw_text)[:8]:
            _append_source_fact(facts, seen, source_type="source_slide", source_id=selected_slide.id, field="raw_text", text=candidate, confidence="high", scope="slide")

    if selected_block is not None:
        _append_source_fact(facts, seen, source_type="source_block", source_id=selected_block.id, field="block_type", text=selected_block.block_type, confidence="medium", scope="block")
        for candidate in _fact_candidates_from_text(selected_block.raw_text or selected_block.normalized_text)[:6]:
            _append_source_fact(facts, seen, source_type="source_block", source_id=selected_block.id, field="raw_text", text=candidate, confidence="high", scope="block")

    return {
        "schemaVersion": "smart-edit-source-facts.v1",
        "rules": [
            "Use only these sourceFacts for factual claims.",
            "Cite fact IDs in source_fact_ids.",
            "Put missing evidence in missing_inputs or quality_warnings instead of inventing facts.",
            "Facts include factType, evidenceStrength, and safetyFlags; do not strengthen facts marked do_not_strengthen.",
        ],
        "factCount": len(facts),
        "facts": facts[:80],
        "factTypeCounts": summarize_fact_types(facts),
        "safetyFlagCounts": summarize_safety_flags(facts),
        "coverage": {
            "hasSelectedSlide": selected_slide is not None,
            "hasSelectedBlock": selected_block is not None,
            "hasInstruction": bool(_normalise_fact_text(instruction)),
            "selectedBlockFactCount": len([fact for fact in facts if fact["sourceType"] == "source_block"]),
        },
    }


def _build_smart_edit_plan(context: dict) -> dict:
    source_fact_package = context.get("sourceFactPackage") if isinstance(context.get("sourceFactPackage"), dict) else {}
    return {
        "schemaVersion": "smart-edit-plan.v1",
        "knowledgeMetadata": context.get("knowledgeMetadata") or {},
        "sourceFactSummary": {
            "schemaVersion": source_fact_package.get("schemaVersion"),
            "factCount": source_fact_package.get("factCount") or 0,
            "coverage": source_fact_package.get("coverage") or {},
        },
        "steps": [
            {"id": "retrieve", "instruction": "Use selected block, selected slide, neighboring slides, archetype knowledge, and source facts."},
            {"id": "draft", "instruction": "Return a reviewable suggestion with source_fact_ids, missing_inputs, and quality_warnings."},
            {"id": "critique", "instruction": "Check fact IDs, unsupported claims, missing evidence, and risk level."},
            {"id": "repair", "instruction": "If critique status is review, make one bounded repair pass."},
            {"id": "persist", "instruction": "Persist suggestion, artifacts, telemetry, and user review state."},
        ],
    }


def _critique_smart_edit_payload(payload: dict[str, object], source_fact_package: dict) -> dict:
    allowed_fact_ids = {
        str(fact.get("id"))
        for fact in source_fact_package.get("facts", [])
        if isinstance(fact, dict) and fact.get("id")
    }
    fact_by_id = {
        str(fact.get("id")): fact
        for fact in source_fact_package.get("facts", [])
        if isinstance(fact, dict) and fact.get("id")
    }
    source_fact_ids = [str(item) for item in payload.get("source_fact_ids", [])] if isinstance(payload.get("source_fact_ids"), list) else []
    missing_inputs = payload.get("missing_inputs") if isinstance(payload.get("missing_inputs"), list) else []
    quality_warnings = payload.get("quality_warnings") if isinstance(payload.get("quality_warnings"), list) else []
    warnings = [str(item) for item in quality_warnings]
    unsupported_fact_ids = [fact_id for fact_id in source_fact_ids if fact_id not in allowed_fact_ids]
    if allowed_fact_ids and not source_fact_ids:
        warnings.append("No source fact IDs were declared in source_fact_ids.")
    if unsupported_fact_ids:
        warnings.append("Some source_fact_ids do not exist in sourceFactPackage facts.")
    cited_safety_flags = sorted(
        {
            str(flag)
            for fact_id in source_fact_ids
            for flag in (fact_by_id.get(str(fact_id), {}).get("safetyFlags") or [])
        }
    )
    cited_fact_types = sorted(
        {
            str(fact_by_id.get(str(fact_id), {}).get("factType"))
            for fact_id in source_fact_ids
            if fact_by_id.get(str(fact_id), {}).get("factType")
        }
    )
    if "requires_source" in cited_safety_flags and not payload.get("source_facts_used"):
        warnings.append("Cited facts require readable source_facts_used labels.")
    unchanged_output = bool(
        _safe_text(payload.get("suggested_text"))
        and _safe_text(payload.get("suggested_text")) == _safe_text(payload.get("original_text"))
    )
    if unchanged_output:
        warnings.append("Suggested text is unchanged from original text.")
    critique_decision = build_critique_decision(
        warnings=warnings,
        missing_inputs=missing_inputs,
        unsupported_fact_ids=unsupported_fact_ids,
        unsupported_facts=[],
        cited_safety_flags=cited_safety_flags,
        unchanged_output=unchanged_output,
    )
    return {
        "schemaVersion": "smart-edit-critique.v1",
        "status": critique_decision.get("status") if critique_decision.get("status") != "blocking" else "review",
        "warningCount": len(warnings),
        "missingInputCount": len(missing_inputs),
        "allowedSourceFactIds": sorted(allowed_fact_ids),
        "sourceFactIds": source_fact_ids,
        "unsupportedSourceFactIds": unsupported_fact_ids,
        "citedFactTypes": cited_fact_types,
        "citedSafetyFlags": cited_safety_flags,
        "warnings": warnings,
        "missingInputs": missing_inputs,
        "decision": critique_decision,
        "dimensions": critique_decision.get("dimensions") or [],
        "repairActions": critique_decision.get("repairActions") or [],
    }


def _record_smart_edit_artifact(
    db: Session,
    *,
    deck_id: str,
    run_id: str,
    artifact_type: str,
    summary: str,
    payload_json: dict,
    metrics_json: dict | None = None,
) -> DeckLlmArtifact:
    canonical_payload = persist_canonical_llm_artifact(
        db,
        deck_id=deck_id,
        artifact_type=artifact_type,
        payload=payload_json,
    )
    stored_metrics = dict(metrics_json or {})
    if canonical_payload:
        stored_metrics.update(
            {
                "canonicalArtifactFilename": canonical_payload["filename"],
                "canonicalArtifactStoragePath": canonical_payload["storagePath"],
            }
        )
        payload_json = {
            **payload_json,
            "canonicalFilename": canonical_payload["filename"],
            "canonicalStoragePath": canonical_payload["storagePath"],
        }
    artifact = DeckLlmArtifact(
        id=generate_id("artifact"),
        deck_id=deck_id,
        extraction_run_id=None,
        artifact_type=artifact_type,
        artifact_key=run_id,
        schema_version=SMART_EDIT_ARTIFACT_SCHEMA_VERSION,
        status="ready",
        summary=summary,
        payload_json=payload_json,
        bucket_payload_key=canonical_payload["storagePath"] if canonical_payload else None,
        metrics_json=stored_metrics,
    )
    db.add(artifact)
    return artifact


def _map_run(run: SmartEditRun) -> dict:
    return {
        "id": run.id,
        "deck_id": run.deck_id,
        "slide_id": run.slide_id,
        "block_id": run.block_id,
        "instruction": run.instruction,
        "audience_type": run.audience_type,
        "created_at": run.created_at.isoformat() if run.created_at else "",
    }


def _map_suggestion(suggestion: SmartEditSuggestion) -> dict:
    return {
        "id": suggestion.id,
        "run_id": suggestion.run_id,
        "deck_id": suggestion.deck_id,
        "slide_id": suggestion.slide_id,
        "block_id": suggestion.block_id,
        "original_text": suggestion.original_text,
        "suggested_text": suggestion.suggested_text,
        "reason": suggestion.reason,
        "risk_level": suggestion.risk_level,
        "status": suggestion.status,
    }


def _load_block(db: Session, deck_id: str, slide_id: str, block_id: str) -> DeckSlideBlock | None:
    return (
        db.query(DeckSlideBlock)
        .join(DeckSlide, DeckSlide.id == DeckSlideBlock.slide_id)
        .join(Deck, Deck.id == DeckSlide.deck_id)
        .filter(
            Deck.id == deck_id,
            DeckSlide.id == slide_id,
            DeckSlideBlock.id == block_id,
        )
        .one_or_none()
    )


def _load_deck_context(db: Session, deck_id: str) -> Deck | None:
    return (
        db.query(Deck)
        .options(selectinload(Deck.slides).selectinload(DeckSlide.blocks))
        .filter(Deck.id == deck_id)
        .one_or_none()
    )


def _smart_edit_context(deck: Deck, slide_id: str, block_id: str, *, instruction: str = "", audience_type: str = "") -> dict:
    slides = sorted(deck.slides, key=lambda item: item.slide_index)
    selected_slide = next((slide for slide in slides if slide.id == slide_id), None)
    selected_block = None
    if selected_slide is not None:
        selected_block = next((block for block in selected_slide.blocks if block.id == block_id), None)
    source_fact_package = _build_smart_edit_source_fact_package(
        deck=deck,
        selected_slide=selected_slide,
        selected_block=selected_block,
        instruction=instruction,
        audience_type=audience_type,
    )
    return {
        "deck": {
            "id": deck.id,
            "title": deck.title,
            "audience": deck.audience,
            "purpose": deck.purpose,
            "summary": deck.summary,
        },
        "selectedSlide": {
            "id": selected_slide.id,
            "title": selected_slide.title,
            "role": selected_slide.role,
            "raw_text": selected_slide.raw_text,
        }
        if selected_slide is not None
        else None,
        "selectedBlock": {
            "id": selected_block.id,
            "block_type": selected_block.block_type,
            "raw_text": selected_block.raw_text,
            "normalized_text": selected_block.normalized_text,
        }
        if selected_block is not None
        else None,
        "neighborSlides": [
            {
                "id": slide.id,
                "title": slide.title,
                "role": slide.role,
                "summary": slide.summary,
            }
            for slide in slides[:12]
        ],
        "slideArchetypeContext": build_slide_archetype_context(
            audience=deck.audience,
            purpose=deck.purpose,
            slide_texts=[selected_slide.raw_text or ""] if selected_slide else [],
            slide_titles=[selected_slide.title or ""] if selected_slide else [],
            slide_roles=[selected_slide.role or ""] if selected_slide else [],
        ),
        "knowledgeMetadata": build_llm_knowledge_metadata(),
        "runtimeContext": build_architecture_runtime_context(),
        "sourceFactPackage": source_fact_package,
    }


def create_smart_edit(
    db: Session,
    *,
    deck_id: str,
    slide_id: str,
    block_id: str,
    instruction: str,
    audience_type: str,
) -> dict | None:
    block = _load_block(db, deck_id, slide_id, block_id)
    if block is None:
        return None
    deck = _load_deck_context(db, deck_id)
    if deck is None:
        return None
    provider_config = _resolve_claude_config(db, deck, use_case="smart_edit")
    knowledge_metadata = build_llm_knowledge_metadata()

    run = SmartEditRun(
        id=generate_id("run"),
        deck_id=deck_id,
        slide_id=slide_id,
        block_id=block_id,
        instruction=instruction,
        audience_type=audience_type,
    )
    db.add(run)
    db.flush()

    try:
        deck_context = _smart_edit_context(deck, slide_id, block_id, instruction=instruction, audience_type=audience_type)
        source_fact_package = deck_context.get("sourceFactPackage") if isinstance(deck_context.get("sourceFactPackage"), dict) else {}
        smart_edit_plan = _build_smart_edit_plan(deck_context)
        _record_smart_edit_artifact(
            db,
            deck_id=deck_id,
            run_id=run.id,
            artifact_type="smart_edit_source_facts",
            summary=f"Source fact package for Smart Edit run {run.id}.",
            payload_json=source_fact_package,
            metrics_json={
                "factCount": source_fact_package.get("factCount"),
                "factTypeCounts": source_fact_package.get("factTypeCounts"),
                "safetyFlagCounts": source_fact_package.get("safetyFlagCounts"),
                "selectedBlockFactCount": (source_fact_package.get("coverage") or {}).get("selectedBlockFactCount"),
                "knowledgeVersion": knowledge_metadata.get("version"),
                "knowledgeSource": knowledge_metadata.get("source"),
                "runtimeContextVersion": (deck_context.get("runtimeContext") or {}).get("schemaVersion"),
            },
        )
        _record_smart_edit_artifact(
            db,
            deck_id=deck_id,
            run_id=run.id,
            artifact_type="smart_edit_plan",
            summary=f"Knowledge-aware Smart Edit plan for run {run.id}.",
            payload_json=smart_edit_plan,
            metrics_json={
                "factCount": source_fact_package.get("factCount"),
                "knowledgeVersion": knowledge_metadata.get("version"),
                "knowledgeSource": knowledge_metadata.get("source"),
                "runtimeContextVersion": (deck_context.get("runtimeContext") or {}).get("schemaVersion"),
            },
        )
        raw_suggestion_payload = smart_edit_run(
            deck_id=deck_id,
            slide_id=slide_id,
            block_id=block_id,
            instruction=instruction,
            audience_type=audience_type,
            original_text=block.raw_text,
            deck_context=deck_context,
            provider_config=provider_config,
        )
        suggestion_payload = _normalize_suggestion_payload(raw_suggestion_payload, original_text=block.raw_text)
        raw_suggestion_payload = {**suggestion_payload, **raw_suggestion_payload}
        smart_edit_critique = _critique_smart_edit_payload(raw_suggestion_payload, source_fact_package)
        repair_performed = False
        if smart_edit_critique.get("status") == "review":
            repair_context = {
                **deck_context,
                "repairContext": {
                    "schemaVersion": "smart-edit-repair-context.v1",
                    "critique": smart_edit_critique,
                    "repairActions": smart_edit_critique.get("repairActions") or [],
                    "instruction": "Repair only the critique issues. Preserve factual claims and cite source_fact_ids.",
                },
            }
            repaired_raw_payload = smart_edit_run(
                deck_id=deck_id,
                slide_id=slide_id,
                block_id=block_id,
                instruction=f"{instruction}\nRepair critique issues: {smart_edit_critique.get('warnings')}",
                audience_type=audience_type,
                original_text=block.raw_text,
                deck_context=repair_context,
                provider_config=provider_config,
            )
            repaired_payload = _normalize_suggestion_payload(repaired_raw_payload, original_text=block.raw_text)
            repaired_raw_payload = {**repaired_payload, **repaired_raw_payload}
            repaired_critique = _critique_smart_edit_payload(repaired_raw_payload, source_fact_package)
            _record_smart_edit_artifact(
                db,
                deck_id=deck_id,
                run_id=run.id,
                artifact_type="smart_edit_repair",
                summary=f"Bounded Smart Edit repair pass for run {run.id}.",
                payload_json={
                    "schemaVersion": "smart-edit-repair.v1",
                    "originalCritique": smart_edit_critique,
                    "repairedCritique": repaired_critique,
                    "knowledgeMetadata": knowledge_metadata,
                },
                metrics_json={
                    "originalCritiqueStatus": smart_edit_critique.get("status"),
                    "repairedCritiqueStatus": repaired_critique.get("status"),
                    "repairedWarningCount": repaired_critique.get("warningCount"),
                    "repairedMissingInputCount": repaired_critique.get("missingInputCount"),
                    "repairedBlockingCount": (repaired_critique.get("decision") or {}).get("blockingCount"),
                    "repairedRepairActionCount": len(repaired_critique.get("repairActions") or []),
                },
            )
            suggestion_payload = repaired_payload
            smart_edit_critique = repaired_critique
            raw_suggestion_payload = repaired_raw_payload
            repair_performed = True
        _record_smart_edit_artifact(
            db,
            deck_id=deck_id,
            run_id=run.id,
            artifact_type="smart_edit_critique",
            summary=f"Knowledge-aware Smart Edit critique for run {run.id}.",
            payload_json={
                "schemaVersion": "smart-edit-critique-artifact.v1",
                "critique": smart_edit_critique,
                "sourceFactIds": raw_suggestion_payload.get("source_fact_ids") if isinstance(raw_suggestion_payload.get("source_fact_ids"), list) else [],
                "sourceFactsUsed": raw_suggestion_payload.get("source_facts_used") if isinstance(raw_suggestion_payload.get("source_facts_used"), list) else [],
                "knowledgeMetadata": knowledge_metadata,
            },
            metrics_json={
                "critiqueStatus": smart_edit_critique.get("status"),
                "critiqueWarningCount": smart_edit_critique.get("warningCount"),
                "critiqueMissingInputCount": smart_edit_critique.get("missingInputCount"),
                "critiqueBlockingCount": (smart_edit_critique.get("decision") or {}).get("blockingCount"),
                "repairActionCount": len(smart_edit_critique.get("repairActions") or []),
                "repairPerformed": repair_performed,
            },
        )

        suggestion = SmartEditSuggestion(
            id=generate_id("smart"),
            run_id=run.id,
            deck_id=deck_id,
            slide_id=slide_id,
            block_id=block_id,
            original_text=suggestion_payload["original_text"],
            suggested_text=suggestion_payload["suggested_text"],
            reason=suggestion_payload["reason"],
            risk_level=suggestion_payload["risk_level"],
            status="pending",
        )
        db.add(suggestion)
        db.commit()
        db.refresh(run)
        db.refresh(suggestion)
        record_agent_event(
            db,
            event_name="ai.smart_edit.completed",
            run_type="smart_edit",
            workspace_id=deck.workspace_id,
            deck_id=deck_id,
            user_id=getattr(deck, "user_id", None),
            run_id=run.id,
            status="completed",
            metadata={
                "slideId": slide_id,
                "blockId": block_id,
                "audienceType": audience_type,
                "riskLevel": suggestion.risk_level,
                "suggestionStatus": suggestion.status,
                "knowledgeVersion": knowledge_metadata.get("version"),
                "knowledgeSource": knowledge_metadata.get("source"),
                "runtimeContextVersion": (deck_context.get("runtimeContext") or {}).get("schemaVersion"),
                "sourceFactCount": source_fact_package.get("factCount"),
                "sourceFactTypeCounts": source_fact_package.get("factTypeCounts"),
                "sourceFactSafetyFlagCounts": source_fact_package.get("safetyFlagCounts"),
                "critiqueStatus": smart_edit_critique.get("status"),
                "critiqueWarningCount": smart_edit_critique.get("warningCount"),
                "critiqueMissingInputCount": smart_edit_critique.get("missingInputCount"),
                "critiqueBlockingCount": (smart_edit_critique.get("decision") or {}).get("blockingCount"),
                "repairActionCount": len(smart_edit_critique.get("repairActions") or []),
                "repairPerformed": repair_performed,
            },
            commit=True,
        )
        return {"run": _map_run(run), "suggestion": _map_suggestion(suggestion)}
    except (KeyError, TypeError, ValueError, SQLAlchemyError) as exc:
        db.rollback()
        record_agent_event(
            db,
            event_name="ai.smart_edit.failed",
            run_type="smart_edit",
            workspace_id=deck.workspace_id,
            deck_id=deck_id,
            user_id=getattr(deck, "user_id", None),
            run_id=run.id,
            event_level="error",
            status="failed",
            error_category=exc.__class__.__name__,
            error_message=str(exc),
            metadata={
                "slideId": slide_id,
                "blockId": block_id,
                "audienceType": audience_type,
                "knowledgeVersion": knowledge_metadata.get("version"),
                "knowledgeSource": knowledge_metadata.get("source"),
                "runtimeContextVersion": (deck_context.get("runtimeContext") or {}).get("schemaVersion"),
            },
            commit=True,
        )
        raise


def get_smart_edit_run(db: Session, deck_id: str, run_id: str) -> dict | None:
    suggestion = (
        db.query(SmartEditSuggestion)
        .filter(SmartEditSuggestion.deck_id == deck_id, SmartEditSuggestion.run_id == run_id)
        .one_or_none()
    )
    return {"suggestion": _map_suggestion(suggestion)} if suggestion is not None else None
