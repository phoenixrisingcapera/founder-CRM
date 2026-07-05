from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
import re
import threading

from cryptography.fernet import InvalidToken
from sqlalchemy.orm import Session, selectinload

from app.ai.anthropic_provider import call_anthropic_message, extract_anthropic_text
from app.ai.openai_provider import call_openai_response, extract_openai_text
from app.ai.openrouter_provider import call_openrouter_chat_completion, extract_openrouter_text
from app.ai.architecture_runtime_context import build_architecture_runtime_context, build_smart_deck_runtime_capabilities
from app.core.config import settings
from app.core.security import generate_id
from app.core.workspace_ai_crypto import get_workspace_ai_fernet
from app.ai.slide_archetypes_context import build_slide_archetype_context
from app.ai.vc_prompt_context import build_vc_prompt_context
from app.services.smart_deck_subject_detection_service import detect_smart_deck_subject
from app.services.agent_telemetry_service import record_agent_event
from app.services.critique_service import build_critique_decision, summarize_critique_decisions
from app.services.deck_retention_service import apply_retention
from app.services.llm_artifact_persistence_service import persist_canonical_llm_artifact
from app.services.llm_knowledge_service import build_llm_knowledge_metadata
from app.services.source_fact_service import classify_source_fact, summarize_fact_types, summarize_safety_flags
from app.services.bucket_artifact_service import get_bucket_artifact_service
from app.db.session import SessionLocal
from app.db.models import (
    AudienceProfile,
    Deck,
    DeckLlmArtifact,
    DeckSlide,
    DeckSlideBlock,
    DesignToken,
    DesignVersion,
    ElementVariationJob,
    GeneratedSlide,
    GeneratedSlideCodeVersion,
    GeneratedSlideElement,
    GeneratedSlideElementVersion,
    GenerationJob,
    SmartDeckMessage,
    SmartDeckPreference,
    SmartDeckWorkspace,
    User,
    Workspace,
    WorkspaceAiCredential,
    WorkspaceAiProviderSetting,
)
from app.schemas.smart_deck import (
    CreateSmartDeckAssistantRunInput,
    CreateSmartDeckGenerationJobInput,
    CreateSmartDeckMessageInput,
    RenderSchema,
    UpdateSmartDeckPreferenceInput,
)
from app.services.smart_deck_retriever_service import (
    build_element_variation_retrieval_context,
    build_slide_generation_retrieval_context,
)


DESIGN_TOKENS = {
    "brand.surface": "#070A12",
    "brand.surfaceAlt": "#111827",
    "brand.heading": "#F8FAFC",
    "brand.body": "#CBD5E1",
    "brand.accent": "#6EE7B7",
    "brand.muted": "#64748B",
}

SMART_DECK_ARTIFACT_SCHEMA_VERSION = "smart-deck-artifacts.v1"
SMART_DECK_GENERATION_ARTIFACT_TYPES = {
    "smart_deck_generation_context",
    "smart_deck_design_version_manifest",
    "generated_slide_render_schema",
    "generated_slide_code_version",
}
SMART_DECK_ASSISTANT_ARTIFACT_TYPE = "smart_deck_assistant_run"
SMART_DECK_ASSISTANT_ARTIFACT_STORAGE_VERSION = "smart-deck-assistant-artifact.v1"

_logger = logging.getLogger(__name__)

ASSISTANT_INTENTS = {
    "market_size": {
        "label": "Market Size Insight",
        "template": "Assess TAM, SAM, and SOM claims through a VC lens: market definition, adoption path, pricing logic, source quality, and which assumptions need diligence before an IC memo.",
        "action": "save_insight",
    },
    "market_research": {
        "label": "Market Research",
        "template": "Summarize market claims, evidence quality, category timing, ICP clarity, buyer urgency, and the specific research needed to turn founder assertions into investor-grade proof.",
        "action": "save_insight",
    },
    "financial_projection": {
        "label": "Financial Projection Review",
        "template": "Review financial projection claims for ARR/MRR logic, gross margin, CAC, payback, burn, runway, hiring plan, and milestone credibility; separate model assumptions from deck-backed facts.",
        "action": "save_insight",
    },
    "competitor_landscape": {
        "label": "Competitor Landscape",
        "template": "Extract competitor positioning and sharpen differentiation around alternatives, incumbents, switching costs, defensibility, and why the company can win a venture-scale wedge.",
        "action": "save_insight",
    },
    "customer_persona": {
        "label": "Customer Persona",
        "template": "Infer customer segments and ICP from the deck, then identify the evidence needed to validate pain frequency, budget owner, buying trigger, sales cycle, and expansion potential.",
        "action": "save_insight",
    },
    "investor_objections": {
        "label": "Investor Objections",
        "template": "Identify likely objections from associates, partners, and IC members; provide the strongest deck-backed responses plus the missing evidence needed to answer each objection credibly.",
        "action": "save_insight",
    },
    "narrative_flow": {
        "label": "Narrative Flow",
        "template": "Critique the deck sequence as an investor decision path: problem urgency, market scale, solution wedge, traction proof, economics, team, risks, and milestone-tied ask.",
        "action": "add_to_slide",
    },
    "slide_critique": {
        "label": "Slide Critique",
        "template": "Critique the selected slide for VC usefulness: claim clarity, evidence density, metric specificity, objection handling, and one concrete update that improves decision readiness.",
        "action": "add_to_slide",
    },
    "due_diligence_risks": {
        "label": "Due Diligence Risks",
        "template": "Find diligence risks, unsupported claims, concentration issues, market/model assumptions, execution dependencies, and follow-up questions a VC team should ask before conviction.",
        "action": "save_insight",
    },
    "missing_evidence": {
        "label": "Missing Evidence",
        "template": "List the missing evidence needed to make selected claims investor-ready: source, date, owner, method, benchmark, customer proof, financial support, and where it belongs in the deck.",
        "action": "save_insight",
    },
    "rewrite_for_vc": {
        "label": "VC Rewrite",
        "template": "Rewrite the selected content for a concise VC pitch while preserving facts, increasing specificity only when supported, and making the investor takeaway explicit.",
        "action": "add_to_slide",
    },
    "create_design_version": {
        "label": "Design Version Brief",
        "template": "Create a design-version brief for Smart Deck generation that states the target VC persona, slide objective, evidence hierarchy, risk handling, and the investor takeaway each slide must land.",
        "action": "create_version",
    },
}

ASSISTANT_OUTPUT_TYPES = {
    "market_size": "insight",
    "market_research": "research",
    "financial_projection": "insight",
    "competitor_landscape": "research",
    "customer_persona": "insight",
    "investor_objections": "insight",
    "narrative_flow": "critique",
    "slide_critique": "critique",
    "due_diligence_risks": "insight",
    "missing_evidence": "insight",
    "rewrite_for_vc": "critique",
    "create_design_version": "design_version",
}

INVALID_GENERATION_PROVIDER_VALUES = {
    "deterministic",
    "fallback",
    "missing",
    "missing_provider",
    "missing_openai",
    "missing_openrouter",
    "missing_claude",
}


class SmartDeckProviderUnavailableError(ValueError):
    """Raised when a redesign or generation request has no usable AI provider."""

ANTHROPIC_MODEL_ALIASES = {
    "claude-sonnet": "claude-sonnet-4-5",
    "claude-opus": "claude-opus-4-1",
}
OPENAI_MODEL_PREFIXES = ("gpt-", "o1", "o3", "o4")


def _normalize_anthropic_model(model: str | None) -> str:
    if not model:
        return settings.anthropic_model
    return ANTHROPIC_MODEL_ALIASES.get(model, model)


def _is_production_mode() -> bool:
    return settings.app_env.lower() == "production" or settings.railway_environment.lower() == "production"


def _is_openai_model(model: str | None) -> bool:
    return bool(model and model.strip().lower().startswith(OPENAI_MODEL_PREFIXES))


def _is_openrouter_model(model: str | None) -> bool:
    return bool(model and "/" in model.strip())


def _is_anthropic_model(model: str | None) -> bool:
    return bool(model and model.strip().lower().startswith("claude"))


def _model_for_provider(provider: str, preferred_model: str | None, setting_model: str | None = None) -> str:
    if provider == "openai":
        if _is_openai_model(preferred_model):
            return preferred_model or settings.openai_model
        if _is_openai_model(setting_model):
            return setting_model or settings.openai_model
        return settings.openai_model
    if provider == "openrouter":
        if _is_openrouter_model(preferred_model):
            return preferred_model or settings.openrouter_model
        if _is_openrouter_model(setting_model):
            return setting_model or settings.openrouter_model
        return settings.openrouter_model
    if _is_anthropic_model(preferred_model):
        return _normalize_anthropic_model(preferred_model)
    if _is_anthropic_model(setting_model):
        return _normalize_anthropic_model(setting_model)
    return settings.anthropic_model


def _provider_from_generation_mode() -> str | None:
    mode = (settings.deck_generation_mode or "claude").strip().lower()
    if mode == "mock":
        raise ValueError("Mock Smart Deck generation has moved to the Deck local_testing harness.")
    if mode == "openai":
        return "openai"
    if mode == "openrouter":
        return "openrouter"
    if mode in {"claude", "anthropic"}:
        return "anthropic"
    return None


def _decrypt_workspace_api_key(credential: WorkspaceAiCredential | None) -> str | None:
    if credential is None or not credential.is_active:
        return None
    try:
        return get_workspace_ai_fernet().decrypt(credential.encrypted_api_key).decode()
    except (InvalidToken, ValueError):
        return None


def _resolve_claude_config(
    db: Session,
    deck: Deck,
    preferred_model: str | None = None,
    *,
    use_case: str = "smart_deck",
) -> dict:
    env_provider = _provider_from_generation_mode()
    env_config = _resolve_environment_provider_config(env_provider, preferred_model)

    setting_query = db.query(WorkspaceAiProviderSetting).filter(
        WorkspaceAiProviderSetting.workspace_id == deck.workspace_id,
        WorkspaceAiProviderSetting.configured_at.is_not(None),
    )
    if use_case == "smart_edit":
        setting_query = setting_query.filter(WorkspaceAiProviderSetting.use_for_smart_edit.is_(True))
    elif use_case == "analysis":
        setting_query = setting_query.filter(WorkspaceAiProviderSetting.use_for_analysis.is_(True))
    else:
        setting_query = setting_query.filter(WorkspaceAiProviderSetting.use_for_smart_deck.is_(True))
    setting = setting_query.first()
    credential = None
    if setting and setting.credential_id and setting.provider in {"openai", "openrouter", "claude"}:
        credential = (
            db.query(WorkspaceAiCredential)
            .filter(
                WorkspaceAiCredential.id == setting.credential_id,
                WorkspaceAiCredential.provider == setting.provider,
                WorkspaceAiCredential.is_active.is_(True),
            )
            .first()
        )
    workspace_api_key = _decrypt_workspace_api_key(credential)
    if workspace_api_key:
        provider = "anthropic" if setting.provider == "claude" else setting.provider
        return {
            "provider": provider,
            "model": _model_for_provider(provider, preferred_model, setting.preferred_model),
            "apiKey": workspace_api_key,
            "source": "workspace",
            "credentialLast4": credential.api_key_last4 if credential else None,
        }

    return env_config


def _resolve_environment_provider_config(provider: str | None, preferred_model: str | None) -> dict:
    if provider == "openai":
        if not settings.openai_api_key and not _is_production_mode():
            return {
                "provider": "deterministic",
                "model": None,
                "apiKey": None,
                "source": "fallback",
            }
        return {
            "provider": "openai" if settings.openai_api_key else "missing_openai",
            "model": _model_for_provider("openai", preferred_model),
            "apiKey": settings.openai_api_key or None,
            "source": "environment" if settings.openai_api_key else "missing",
        }
    if provider == "openrouter":
        if not settings.openrouter_api_key and not _is_production_mode():
            return {
                "provider": "deterministic",
                "model": None,
                "apiKey": None,
                "source": "fallback",
            }
        return {
            "provider": "openrouter" if settings.openrouter_api_key else "missing_openrouter",
            "model": _model_for_provider("openrouter", preferred_model),
            "apiKey": settings.openrouter_api_key or None,
            "source": "environment" if settings.openrouter_api_key else "missing",
        }
    if provider == "anthropic":
        if not settings.anthropic_api_key and not _is_production_mode():
            return {
                "provider": "deterministic",
                "model": None,
                "apiKey": None,
                "source": "fallback",
            }
        return {
            "provider": "anthropic" if settings.anthropic_api_key else "missing_claude",
            "model": _model_for_provider("anthropic", preferred_model),
            "apiKey": settings.anthropic_api_key or None,
            "source": "environment" if settings.anthropic_api_key else "missing",
        }
    if settings.openai_api_key:
        return {
            "provider": "openai",
            "model": _model_for_provider("openai", preferred_model),
            "apiKey": settings.openai_api_key,
            "source": "environment",
        }
    if settings.openrouter_api_key:
        return {
            "provider": "openrouter",
            "model": _model_for_provider("openrouter", preferred_model),
            "apiKey": settings.openrouter_api_key,
            "source": "environment",
        }
    if not _is_production_mode():
        return {
            "provider": "deterministic",
            "model": None,
            "apiKey": None,
            "source": "fallback",
        }
    return {
        "provider": "anthropic" if settings.anthropic_api_key else "missing_provider",
        "model": _model_for_provider("anthropic", preferred_model),
        "apiKey": settings.anthropic_api_key or None,
        "source": "environment" if settings.anthropic_api_key else "missing",
    }


def get_generation_provider_config(
    db: Session,
    deck: Deck,
    preferred_model: str | None,
    *,
    strict: bool = False,
    use_case: str = "smart_deck",
) -> dict:
    config = _resolve_claude_config(db, deck, preferred_model, use_case=use_case)
    if strict and config.get("provider") in INVALID_GENERATION_PROVIDER_VALUES:
        raise SmartDeckProviderUnavailableError("AI generation provider is unavailable.")
    if strict and not config.get("apiKey"):
        raise SmartDeckProviderUnavailableError("AI generation provider credentials are missing.")
    return config


def _build_deterministic_render_payload(selected_slides: list[DeckSlide], prompt: str) -> dict:
    return {
        "designVersionName": "Deterministic Smart Deck Preview",
        "slides": [
            {
                "sourceSlideId": slide.id,
                "slideNumber": idx + 1,
                "title": slide.title or f"Slide {idx + 1}",
                "renderSchema": _build_render_schema(slide, prompt),
            }
            for idx, slide in enumerate(selected_slides)
        ],
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _public_asset_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith(("http://", "https://", "/api/", "/uploads/", "/static/", "data:")):
        return path
    if path.startswith("/home/") or path.startswith("/tmp/"):
        return None
    return f"/{path.lstrip('/')}"


def _load_deck(db: Session, deck_id: str) -> Deck | None:
    return (
        db.query(Deck)
        .options(
            selectinload(Deck.slides).selectinload(DeckSlide.blocks),
            selectinload(Deck.slides).selectinload(DeckSlide.assets),
            selectinload(Deck.workspace).selectinload(Workspace.user).selectinload(User.profile),
            selectinload(Deck.workspace).selectinload(Workspace.company_profiles),
            selectinload(Deck.generation_jobs),
            selectinload(Deck.design_versions).selectinload(DesignVersion.generated_slides).selectinload(GeneratedSlide.code_versions),
            selectinload(Deck.design_versions)
            .selectinload(DesignVersion.generated_slides)
            .selectinload(GeneratedSlide.elements)
            .selectinload(GeneratedSlideElement.versions),
            selectinload(Deck.llm_artifacts),
            selectinload(Deck.brand_profile),
            selectinload(Deck.smart_deck_workspace).selectinload(SmartDeckWorkspace.preference),
            selectinload(Deck.smart_deck_workspace).selectinload(SmartDeckWorkspace.messages),
            selectinload(Deck.design_tokens),
        )
        .filter(Deck.id == deck_id)
        .first()
    )


def _load_audience_profile(db: Session, audience: str | None) -> dict | None:
    if not audience:
        return None
    profile = db.query(AudienceProfile).filter(AudienceProfile.label == audience).first()
    if profile is None:
        profile = db.query(AudienceProfile).filter(AudienceProfile.label.ilike(f"%{audience}%")).first()
    if profile is None:
        return None
    return {
        "label": profile.label,
        "focus": profile.focus,
        "tone": profile.tone,
    }


def _source_slide_number(slide: DeckSlide) -> int:
    return slide.slide_number or slide.source_page_number or slide.slide_index + 1


def _map_source_slide(slide: DeckSlide) -> dict:
    blocks = sorted(slide.blocks, key=lambda item: item.block_index)
    preview_url = (
        f"/api/decks/{slide.deck_id}/slides/{slide.id}/preview"
        if slide.rendered_image_path or slide.thumbnail_path
        else None
    )
    layout_hints = {
        "role": slide.semantic_slide_type or slide.role,
        "hasLargeTitle": bool(slide.title),
        "hasPreview": bool(slide.rendered_image_path or slide.thumbnail_path),
        "blockCount": len(blocks),
        "assetCount": len(slide.assets),
    }
    return {
        "id": slide.id,
        "deckId": slide.deck_id,
        "slideNumber": _source_slide_number(slide),
        "title": slide.title,
        "extractedText": slide.raw_text,
        "thumbnailUrl": preview_url,
        "previewImageUrl": preview_url,
        "layoutHints": layout_hints,
        "blocks": [
            {
                "id": block.id,
                "blockIndex": block.block_index,
                "type": block.block_type,
                "text": block.raw_text,
                "normalizedText": block.normalized_text,
            }
            for block in blocks
        ],
    }


def _map_job(job: GenerationJob) -> dict:
    return {
        "id": job.id,
        "deckId": job.deck_id,
        "status": job.status,
        "provider": job.provider,
        "model": job.model,
        "prompt": job.prompt,
        "selectedSourceSlideIds": job.selected_source_slide_ids_json or [],
        "styleId": job.style_id,
        "brandProductId": job.brand_product_id,
        "errorMessage": job.error_message,
        "createdAt": _iso(job.created_at) or "",
        "updatedAt": _iso(job.updated_at) or "",
        "completedAt": _iso(job.completed_at),
    }


def _map_generated_slide(slide: GeneratedSlide) -> dict:
    latest_code = _latest_code_version(slide)
    current_code = _current_code_version(slide) or latest_code
    source_slide = getattr(slide, "source_slide", None)
    bucket_artifacts = _map_bucket_artifacts(current_code)
    return {
        "id": slide.id,
        "deckId": slide.deck_id,
        "designVersionId": slide.design_version_id,
        "generationJobId": slide.generation_job_id,
        "sourceSlideId": slide.source_slide_id,
        "slideNumber": slide.slide_number,
        "title": slide.title,
        "status": slide.status,
        "renderSchema": RenderSchema.model_validate(slide.render_schema_json).model_dump(),
        "designTokens": slide.design_tokens_json,
        "previewImageUrl": _public_asset_url(slide.preview_image_url),
        "validationStatus": slide.validation_status,
        "elements": [_map_generated_slide_element(element) for element in sorted(slide.elements, key=lambda item: item.z_index)],
        "createdAt": _iso(slide.created_at) or "",
        "updatedAt": _iso(slide.updated_at) or "",
        "generated_slide_id": slide.id,
        "slide_index": slide.slide_number,
        "archetype_id": getattr(source_slide, "role", None),
        "current_version_id": slide.current_version_id or (current_code.id if current_code else None),
        "current_design_version_id": slide.design_version_id,
        "version_number": current_code.version_number if current_code else None,
        "render_schema_json": RenderSchema.model_validate(slide.render_schema_json).model_dump(),
        "bucket_render_schema_key": _render_schema_bucket_key(slide, current_code),
        "bucket_code_key": bucket_artifacts.get("code_key"),
        "bucket_artifacts": bucket_artifacts,
    }


def _map_generated_slide_element_version(version: GeneratedSlideElementVersion) -> dict:
    return {
        "id": version.id,
        "elementId": version.element_id,
        "generatedSlideId": version.generated_slide_id,
        "designVersionId": version.design_version_id,
        "versionNumber": version.version_number,
        "source": version.source,
        "status": version.status,
        "style": version.style_json,
        "content": version.content_json,
        "changeSummary": version.change_summary,
        "createdAt": _iso(version.created_at) or "",
    }


def _map_generated_slide_element(element: GeneratedSlideElement) -> dict:
    versions = sorted(element.versions, key=lambda item: item.version_number, reverse=True)
    return {
        "id": element.id,
        "generatedSlideId": element.generated_slide_id,
        "deckId": element.deck_id,
        "designVersionId": element.design_version_id,
        "sourceSlideId": element.source_slide_id,
        "elementKey": element.element_key,
        "elementType": element.element_type,
        "parentElementId": element.parent_element_id,
        "zIndex": element.z_index,
        "x": element.x,
        "y": element.y,
        "width": element.width,
        "height": element.height,
        "rotation": element.rotation,
        "locked": element.locked,
        "visible": element.visible,
        "style": element.style_json,
        "content": element.content_json,
        "versions": [_map_generated_slide_element_version(version) for version in versions],
        "createdAt": _iso(element.created_at) or "",
        "updatedAt": _iso(element.updated_at) or "",
    }


def _map_design_version(version: DesignVersion) -> dict:
    slides = sorted(version.generated_slides, key=lambda item: item.slide_number)
    changed_slide_ids = [slide.source_slide_id or slide.id for slide in slides]
    return {
        "id": version.id,
        "deckId": version.deck_id,
        "generationJobId": version.generation_job_id,
        "name": version.name,
        "status": version.status,
        "isActive": version.is_active,
        "summary": version.summary,
        "generatedSlides": [_map_generated_slide(slide) for slide in slides],
        "createdAt": _iso(version.created_at) or "",
        "updatedAt": _iso(version.updated_at) or "",
        "appliedAt": _iso(version.applied_at),
        "discardedAt": _iso(version.discarded_at),
        "state": _design_version_state(version),
        "source": _design_version_source(version),
        "changed_slide_ids": changed_slide_ids,
        "created_at": _iso(version.created_at) or "",
    }


def _map_code_version(code_version: GeneratedSlideCodeVersion) -> dict:
    return {
        "id": code_version.id,
        "generatedSlideId": code_version.generated_slide_id,
        "versionNumber": code_version.version_number,
        "codeKind": code_version.code_kind,
        "schemaVersion": code_version.schema_version,
        "renderSchema": RenderSchema.model_validate(code_version.render_schema_json).model_dump(),
        "codeJson": code_version.code_json,
        "bucketRenderSchemaKey": code_version.bucket_render_schema_key,
        "bucketCodeKey": code_version.bucket_code_key,
        "bucketThumbnailKey": code_version.bucket_thumbnail_key,
        "status": code_version.status,
        "validationErrors": code_version.validation_errors_json,
        "createdAt": _iso(code_version.created_at) or "",
    }


def _latest_code_version(slide: GeneratedSlide) -> GeneratedSlideCodeVersion | None:
    code_versions = list(getattr(slide, "code_versions", []) or [])
    if not code_versions:
        return None
    return sorted(code_versions, key=lambda item: item.version_number, reverse=True)[0]


def _current_code_version(slide: GeneratedSlide) -> GeneratedSlideCodeVersion | None:
    current_version_id = getattr(slide, "current_version_id", None)
    if not current_version_id:
        return None
    return next((version for version in list(getattr(slide, "code_versions", []) or []) if version.id == current_version_id), None)


def _render_schema_bucket_key(slide: GeneratedSlide, code_version: GeneratedSlideCodeVersion | None) -> str | None:
    if code_version is None:
        return None
    if code_version.bucket_render_schema_key:
        return code_version.bucket_render_schema_key
    code_json = code_version.code_json if isinstance(code_version.code_json, dict) else {}
    storage_path = code_json.get("bucketRenderSchemaKey") or code_json.get("renderSchemaStoragePath")
    if isinstance(storage_path, str):
        return storage_path
    return (
        f"decks/{slide.deck_id}/design-versions/{slide.design_version_id}/slides/"
        f"{slide.id}/code-versions/{code_version.id}/render_schema.json"
    )


def _map_bucket_artifacts(code_version: GeneratedSlideCodeVersion | None) -> dict:
    if code_version is None:
        return {}
    code_json = code_version.code_json if isinstance(code_version.code_json, dict) else {}
    return {
        "render_schema_key": code_version.bucket_render_schema_key or code_json.get("bucketRenderSchemaKey") or code_json.get("renderSchemaStoragePath"),
        "code_key": code_version.bucket_code_key or code_json.get("bucketCodeJsonKey") or code_json.get("codeJsonStoragePath"),
        "thumbnail_key": code_version.bucket_thumbnail_key or code_json.get("bucketThumbnailKey"),
        "render_schema_url": None,
        "thumbnail_url": None,
    }


def _design_version_state(version: DesignVersion) -> str:
    if version.status == "archived":
        return "archived"
    if version.status == "discarded":
        return "discarded"
    if version.is_active or version.status in {"applied", "saved"}:
        return "saved"
    return "preview"


def _design_version_source(version: DesignVersion) -> str:
    if version.status == "restored":
        return "restore"
    if version.generation_job_id:
        return "smart_edit"
    return "manual"


def _map_product_spine_slide(slide: GeneratedSlide) -> dict:
    mapped = _map_generated_slide(slide)
    return {
        "generated_slide_id": mapped["generated_slide_id"],
        "slide_index": mapped["slide_index"],
        "title": mapped["title"],
        "archetype_id": mapped["archetype_id"],
        "current_version_id": mapped["current_version_id"],
        "current_design_version_id": mapped["current_design_version_id"],
        "version_number": mapped["version_number"],
        "render_schema_json": mapped["render_schema_json"],
    }


def _map_product_spine_design_version(version: DesignVersion) -> dict:
    mapped = _map_design_version(version)
    return {
        "id": mapped["id"],
        "state": mapped["state"],
        "source": mapped["source"],
        "changed_slide_ids": mapped["changed_slide_ids"],
        "created_at": mapped["created_at"],
    }


def _set_code_version_lifecycle(code_version: GeneratedSlideCodeVersion, lifecycle: str) -> None:
    code_json = code_version.code_json if isinstance(code_version.code_json, dict) else {}
    code_version.code_json = {**code_json, "lifecycle": lifecycle}


def _code_version_lifecycle(code_version: GeneratedSlideCodeVersion) -> str | None:
    code_json = code_version.code_json if isinstance(code_version.code_json, dict) else {}
    lifecycle = code_json.get("lifecycle") or code_json.get("state")
    return lifecycle if isinstance(lifecycle, str) else None


def _record_design_version_snapshot_artifact(db: Session, deck_id: str, version: DesignVersion, reason: str) -> None:
    slides = sorted(version.generated_slides, key=lambda item: item.slide_number)
    _record_llm_artifact(
        db,
        deck_id=deck_id,
        artifact_type="design_version_slide_versions_snapshot",
        artifact_key=f"{version.id}:{reason}",
        summary=f"Design version slide snapshot for {version.id} ({reason}).",
        payload_json={
            "designVersionId": version.id,
            "reason": reason,
            "slides": [_map_product_spine_slide(slide) for slide in slides],
        },
        metrics_json={"slideCount": len(slides)},
    )


def _design_version_manifest_payload(version: DesignVersion, state: str, reason: str | None = None) -> dict:
    slides = sorted(version.generated_slides, key=lambda item: item.slide_number)
    return {
        "deck_id": version.deck_id,
        "design_version_id": version.id,
        "designVersionId": version.id,
        "state": state,
        "status": version.status,
        "isActive": version.is_active,
        "reason": reason,
        "generationJobId": version.generation_job_id,
        "generatedSlideIds": [slide.id for slide in slides],
        "slides": [
            {
                "generated_slide_id": slide.id,
                "source_slide_id": slide.source_slide_id,
                "current_version_id": slide.current_version_id,
                "render_schema_json_cached": bool(slide.render_schema_json),
                "code_versions": [
                    {
                        "code_version_id": code_version.id,
                        "lifecycle": _code_version_lifecycle(code_version),
                        "render_schema_key": code_version.bucket_render_schema_key,
                        "code_key": code_version.bucket_code_key,
                        "thumbnail_key": code_version.bucket_thumbnail_key,
                    }
                    for code_version in sorted(slide.code_versions, key=lambda item: item.version_number)
                ],
            }
            for slide in slides
        ],
        "updatedAt": datetime.utcnow().isoformat() + "Z",
    }


def _rewrite_design_version_manifest(db: Session, version: DesignVersion, state: str, reason: str) -> None:
    payload = _design_version_manifest_payload(version, state, reason)
    manifest_artifact = _write_design_version_manifest_json_artifact(
        user_id=version.deck.user_id if version.deck else None,
        deck_id=version.deck_id,
        design_version_id=version.id,
        manifest_json=payload,
    )
    version.bucket_manifest_key = manifest_artifact["storagePath"]
    _record_llm_artifact(
        db,
        deck_id=version.deck_id,
        artifact_type="smart_deck_design_version_manifest",
        artifact_key=f"{version.id}:{reason}",
        summary=f"Manifest for Smart Deck design version {version.id} updated to {state}.",
        payload_json={
            **payload,
            "bucketManifestKey": manifest_artifact["storagePath"],
            "manifestHash": manifest_artifact["manifestHash"],
        },
        metrics_json={"generatedSlideCount": len(version.generated_slides)},
    )


def _map_workspace_state(workspace: SmartDeckWorkspace) -> dict:
    return {
        "id": workspace.id,
        "deckId": workspace.deck_id,
        "userId": workspace.user_id,
        "activeDesignVersionId": workspace.active_design_version_id,
        "activeSourceSlideId": workspace.active_source_slide_id,
        "activeGeneratedSlideId": workspace.active_generated_slide_id,
        "selectedElementId": workspace.selected_element_id,
        "status": workspace.status,
        "createdAt": _iso(workspace.created_at) or "",
        "updatedAt": _iso(workspace.updated_at) or "",
    }


def _map_preference(preference: SmartDeckPreference) -> dict:
    return {
        "id": preference.id,
        "workspaceId": preference.workspace_id,
        "deckId": preference.deck_id,
        "userId": preference.user_id,
        "selectedSourceSlideIds": preference.selected_source_slide_ids_json or [],
        "activeSourceSlideId": preference.active_source_slide_id,
        "activeDesignVersionId": preference.active_design_version_id,
        "activeGeneratedSlideId": preference.active_generated_slide_id,
        "selectedElementId": preference.selected_element_id,
        "audience": preference.audience,
        "deckType": preference.deck_type,
        "preferredModel": preference.preferred_model,
        "selectedSubject": preference.selected_subject,
        "selectedActionId": preference.selected_action_id,
        "zoomLevel": preference.zoom_level,
        "canvasFitMode": preference.canvas_fit_mode,
        "rightPanelOpen": preference.right_panel_open,
        "slideRailOpen": preference.slide_rail_open,
        "updatedAt": _iso(preference.updated_at) or "",
    }


def _map_message(message: SmartDeckMessage) -> dict:
    return {
        "id": message.id,
        "workspaceId": message.workspace_id,
        "deckId": message.deck_id,
        "generationJobId": message.generation_job_id,
        "role": message.role,
        "content": message.content,
        "selectedSourceSlideIds": message.selected_source_slide_ids_json or [],
        "metadata": message.metadata_json,
        "createdAt": _iso(message.created_at) or "",
    }


def _map_design_token(token: DesignToken) -> dict:
    return {
        "id": token.id,
        "deckId": token.deck_id,
        "designVersionId": token.design_version_id,
        "generatedSlideId": token.generated_slide_id,
        "tokenName": token.token_name,
        "tokenValue": token.token_value,
        "tokenType": token.token_type,
        "source": token.source,
        "createdAt": _iso(token.created_at) or "",
        "updatedAt": _iso(token.updated_at) or "",
    }


def _ensure_workspace_state(db: Session, deck: Deck) -> tuple[SmartDeckWorkspace, SmartDeckPreference]:
    workspace = db.query(SmartDeckWorkspace).filter(SmartDeckWorkspace.deck_id == deck.id).first()
    if workspace is None:
        workspace = SmartDeckWorkspace(
            id=generate_id("sdws"),
            deck_id=deck.id,
            user_id=deck.user_id,
            status="ready",
        )
        db.add(workspace)
        db.flush()

    preference = db.query(SmartDeckPreference).filter(SmartDeckPreference.workspace_id == workspace.id).first()
    if preference is None:
        first_slide = sorted(deck.slides, key=lambda item: item.slide_index)[0] if deck.slides else None
        active_version = next((version for version in deck.design_versions if version.is_active), None)
        active_slides = sorted(active_version.generated_slides, key=lambda item: item.slide_number) if active_version else []
        preference = SmartDeckPreference(
            id=generate_id("sdpref"),
            workspace_id=workspace.id,
            deck_id=deck.id,
            user_id=deck.user_id,
            selected_source_slide_ids_json=[first_slide.id] if first_slide else [],
            active_source_slide_id=workspace.active_source_slide_id or (first_slide.id if first_slide else None),
            active_design_version_id=workspace.active_design_version_id or (active_version.id if active_version else None),
            active_generated_slide_id=workspace.active_generated_slide_id or (active_slides[0].id if active_slides else None),
            audience=deck.audience,
            deck_type="vc_fund_pitch" if deck.audience and any(marker in deck.audience.lower() for marker in ("lp", "fund", "partner")) else "startup_pitch",
            preferred_model=settings.anthropic_model,
            selected_subject=first_slide.role if first_slide else None,
        )
        db.add(preference)
        db.flush()

    return workspace, preference


def _record_smart_deck_message(
    db: Session,
    *,
    workspace_id: str,
    deck_id: str,
    role: str,
    content: str,
    generation_job_id: str | None = None,
    selected_source_slide_ids: list[str] | None = None,
    metadata_json: dict | None = None,
) -> SmartDeckMessage:
    message = SmartDeckMessage(
        id=generate_id("sdmsg"),
        workspace_id=workspace_id,
        deck_id=deck_id,
        generation_job_id=generation_job_id,
        role=role,
        content=content,
        selected_source_slide_ids_json=selected_source_slide_ids or [],
        metadata_json=metadata_json,
    )
    db.add(message)
    return message


def _record_design_tokens(db: Session, *, deck_id: str, design_version_id: str, generated_slide_id: str | None = None) -> None:
    for token_name, token_value in DESIGN_TOKENS.items():
        db.add(
            DesignToken(
                id=generate_id("dstok"),
                deck_id=deck_id,
                design_version_id=design_version_id,
                generated_slide_id=generated_slide_id,
                token_name=token_name,
                token_value=token_value,
                token_type="color",
                source="smart_deck_llm",
            )
        )


def _render_element_type(schema_type: str) -> str:
    if schema_type == "chart_placeholder":
        return "chart"
    return schema_type


def _persist_generated_slide_elements(
    db: Session,
    *,
    deck_id: str,
    design_version_id: str,
    generated_slide: GeneratedSlide,
    source_slide_id: str | None,
    render_schema: dict,
) -> list[GeneratedSlideElement]:
    persisted: list[GeneratedSlideElement] = []
    for z_index, render_element in enumerate(render_schema.get("elements", []), start=1):
        element_id = generate_id("gselem")
        style_json = {
            key: render_element.get(key)
            for key in ["fontSize", "fontWeight", "colorToken", "fillToken", "assetUrl"]
            if render_element.get(key) is not None
        }
        content_json = {
            "text": render_element.get("text"),
            "renderElementId": render_element.get("id"),
            "renderType": render_element.get("type"),
            "analyticsKey": render_element.get("analyticsKey"),
        }
        element = GeneratedSlideElement(
            id=element_id,
            generated_slide_id=generated_slide.id,
            deck_id=deck_id,
            design_version_id=design_version_id,
            source_slide_id=source_slide_id,
            element_key=str(render_element.get("id") or element_id),
            element_type=_render_element_type(str(render_element.get("type") or "shape")),
            z_index=int(render_element.get("zIndex") or z_index),
            x=int(render_element.get("x") or 0),
            y=int(render_element.get("y") or 0),
            width=int(render_element.get("width") or 1),
            height=int(render_element.get("height") or 1),
            rotation=0,
            locked=False,
            visible=True,
            style_json=style_json,
            content_json=content_json,
        )
        db.add(element)
        db.flush()
        db.add(
            GeneratedSlideElementVersion(
                id=generate_id("gsever"),
                element_id=element.id,
                generated_slide_id=generated_slide.id,
                design_version_id=design_version_id,
                version_number=1,
                source="initial_generation",
                status="active",
                style_json=style_json,
                content_json=content_json,
                change_summary="Initial element version from validated render_schema_json.",
            )
        )
        persisted.append(element)
    return persisted


SOURCE_FACT_MAX_TEXT_LENGTH = 320
SOURCE_FACT_MAX_PER_SLIDE = 8


def _normalise_fact_text(value: object, *, limit: int = SOURCE_FACT_MAX_TEXT_LENGTH) -> str:
    text = str(value if value is not None else "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:limit].strip()


def _fact_candidates_from_text(text: str | None) -> list[str]:
    normalised = _normalise_fact_text(text, limit=5000)
    if not normalised:
        return []
    parts = [
        part.strip(" -:\t")
        for part in re.split(r"(?<=[.!?])\s+|\n+|[•·]\s*", normalised)
        if part.strip(" -:\t")
    ]
    if len(parts) <= 1:
        parts = [
            part.strip(" -:\t")
            for part in re.split(r"\s{2,}|;\s+", normalised)
            if part.strip(" -:\t")
        ]
    return [_normalise_fact_text(part) for part in parts if len(part) >= 8]


def _append_source_fact(
    facts: list[dict],
    seen: set[str],
    *,
    source_type: str,
    source_id: str,
    text: object,
    confidence: str,
    scope: str,
    field: str | None = None,
) -> None:
    fact_text = _normalise_fact_text(text)
    if not fact_text:
        return
    key = f"{source_type}:{source_id}:{field or ''}:{fact_text.lower()}"
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


def _extract_artifact_fact_texts(artifact_context: object, *, limit: int = 12) -> list[str]:
    if not isinstance(artifact_context, dict):
        return []
    candidates: list[str] = []

    def walk(value: object) -> None:
        if len(candidates) >= limit:
            return
        if isinstance(value, str):
            text = _normalise_fact_text(value)
            if text and len(text) >= 12:
                candidates.append(text)
            return
        if isinstance(value, list):
            for item in value[:limit]:
                walk(item)
                if len(candidates) >= limit:
                    break
            return
        if isinstance(value, dict):
            for key in ("summary", "headline", "title", "description", "text", "claim", "finding", "value"):
                if key in value:
                    walk(value.get(key))
                    if len(candidates) >= limit:
                        return
            for item in list(value.values())[:limit]:
                walk(item)
                if len(candidates) >= limit:
                    return

    walk(artifact_context)
    return candidates[:limit]


def _build_source_fact_package(
    *,
    deck: Deck,
    selected_slides: list[DeckSlide],
    payload: CreateSmartDeckGenerationJobInput,
    brand_profile,
    prompt_context_artifact: object,
) -> dict:
    facts: list[dict] = []
    seen: set[str] = set()

    _append_source_fact(
        facts,
        seen,
        source_type="deck_metadata",
        source_id=deck.id,
        field="title",
        text=deck.title,
        confidence="high",
        scope="deck",
    )
    _append_source_fact(
        facts,
        seen,
        source_type="deck_metadata",
        source_id=deck.id,
        field="audience",
        text=deck.audience,
        confidence="high",
        scope="deck",
    )
    _append_source_fact(
        facts,
        seen,
        source_type="deck_metadata",
        source_id=deck.id,
        field="purpose",
        text=deck.purpose,
        confidence="high",
        scope="deck",
    )
    _append_source_fact(
        facts,
        seen,
        source_type="deck_metadata",
        source_id=deck.id,
        field="summary",
        text=deck.summary,
        confidence="medium",
        scope="deck",
    )
    _append_source_fact(
        facts,
        seen,
        source_type="user_instruction",
        source_id=deck.id,
        field="prompt",
        text=payload.prompt,
        confidence="high",
        scope="job",
    )
    _append_source_fact(
        facts,
        seen,
        source_type="user_instruction",
        source_id=deck.id,
        field="additionalContext",
        text=payload.additionalContext,
        confidence="medium",
        scope="job",
    )

    if brand_profile is not None:
        _append_source_fact(
            facts,
            seen,
            source_type="brand_profile",
            source_id=getattr(brand_profile, "id", deck.id),
            field="company_name",
            text=getattr(brand_profile, "company_name", None),
            confidence="medium",
            scope="brand",
        )
        _append_source_fact(
            facts,
            seen,
            source_type="brand_profile",
            source_id=getattr(brand_profile, "id", deck.id),
            field="visual_direction",
            text=getattr(brand_profile, "visual_direction", None),
            confidence="medium",
            scope="brand",
        )

    for slide in selected_slides:
        _append_source_fact(
            facts,
            seen,
            source_type="source_slide",
            source_id=slide.id,
            field="title",
            text=slide.title,
            confidence="high",
            scope="slide",
        )
        _append_source_fact(
            facts,
            seen,
            source_type="source_slide",
            source_id=slide.id,
            field="role",
            text=slide.role or slide.semantic_slide_type,
            confidence="medium",
            scope="slide",
        )
        for candidate in _fact_candidates_from_text(slide.raw_text)[:SOURCE_FACT_MAX_PER_SLIDE]:
            _append_source_fact(
                facts,
                seen,
                source_type="source_slide",
                source_id=slide.id,
                field="raw_text",
                text=candidate,
                confidence="high",
                scope="slide",
            )

    for text in _extract_artifact_fact_texts(prompt_context_artifact):
        _append_source_fact(
            facts,
            seen,
            source_type="llm_artifact",
            source_id=deck.id,
            field="prompt_context",
            text=text,
            confidence="medium",
            scope="deck",
        )

    slide_fact_counts = {
        slide.id: len([fact for fact in facts if fact["sourceType"] == "source_slide" and fact["sourceId"] == slide.id])
        for slide in selected_slides
    }
    missing_slide_fact_ids = [slide.id for slide in selected_slides if slide_fact_counts.get(slide.id, 0) <= 1]
    return {
        "schemaVersion": "smart-deck-source-facts.v1",
        "rules": [
            "Use only these sourceFacts for factual claims.",
            "If a needed fact is missing, put the gap in renderSchema.analytics.missingInputs.",
            "Do not upgrade weak facts into metrics, customer names, commitments, returns, legal claims, or regulatory claims.",
            "Every generated slide should list relevant fact IDs in renderSchema.analytics.sourceFactIds.",
            "Every generated slide should list readable fact labels or excerpts in renderSchema.analytics.sourceFactsUsed.",
            "Facts include factType, evidenceStrength, and safetyFlags; do not strengthen facts marked do_not_strengthen.",
        ],
        "factCount": len(facts),
        "facts": facts[:80],
        "factTypeCounts": summarize_fact_types(facts),
        "safetyFlagCounts": summarize_safety_flags(facts),
        "coverage": {
            "selectedSlideCount": len(selected_slides),
            "sourceSlideFactCounts": slide_fact_counts,
            "missingSlideFactIds": missing_slide_fact_ids,
            "hasUserInstruction": bool(_normalise_fact_text(payload.prompt)),
            "hasAdditionalContext": bool(_normalise_fact_text(payload.additionalContext)),
            "hasPromptContextArtifact": isinstance(prompt_context_artifact, dict),
        },
    }


def _build_llm_context(
    deck: Deck,
    selected_slides: list[DeckSlide],
    payload: CreateSmartDeckGenerationJobInput,
    audience_profile: dict | None = None,
) -> dict:
    brand_profile = deck.brand_profile
    prompt_context_artifact = next(
        (
            artifact.payload_json
            for artifact in deck.llm_artifacts
            if artifact.artifact_type == "prompt_context" and artifact.status == "ready"
        ),
        None,
    )
    active_design_version = next((version for version in deck.design_versions if version.is_active), None)
    archetype_context = build_slide_archetype_context(
        audience=deck.audience,
        purpose=deck.purpose,
        slide_texts=[slide.raw_text or "" for slide in selected_slides],
        slide_titles=[slide.title or "" for slide in selected_slides],
        slide_roles=[slide.role or "" for slide in selected_slides],
    )
    knowledge_metadata = build_llm_knowledge_metadata()
    detected_subjects = [
        {
            **detect_smart_deck_subject(slide.title, slide.raw_text, [slide.role, slide.semantic_slide_type] if slide.semantic_slide_type else [slide.role]),
            "slideId": slide.id,
            "slideTitle": slide.title,
        }
        for slide in selected_slides
    ]
    selected_subject = payload.selectedSubject or (detected_subjects[0]["subject"] if detected_subjects else None)
    retrieval_context = build_slide_generation_retrieval_context(
        deck=deck,
        selected_slides=selected_slides,
        active_design_version=active_design_version,
        prompt=payload.prompt,
        additional_context=payload.additionalContext,
        design_tokens=DESIGN_TOKENS,
        artifact_context=prompt_context_artifact,
        audience_context=build_vc_prompt_context(
            audience=deck.audience,
            purpose=deck.purpose,
            user_role=deck.workspace.user.role if deck.workspace and deck.workspace.user else None,
            audience_profile=audience_profile,
            deck_metadata=deck.metadata_json,
            brand_evidence=brand_profile.raw_evidence_json if brand_profile else None,
            slide_texts=[slide.raw_text or "" for slide in selected_slides],
        ),
        archetype_context=archetype_context,
    )
    audience_context = retrieval_context["audienceContext"]
    source_fact_package = _build_source_fact_package(
        deck=deck,
        selected_slides=selected_slides,
        payload=payload,
        brand_profile=brand_profile,
        prompt_context_artifact=prompt_context_artifact,
    )
    runtime_context = build_architecture_runtime_context()
    runtime_capabilities = build_smart_deck_runtime_capabilities()
    return {
        "deck": {
            "id": deck.id,
            "title": deck.title,
            "audience": deck.audience,
            "purpose": deck.purpose,
            "summary": deck.summary,
        },
        "brand": {
            "name": brand_profile.company_name if brand_profile else "Deck AI Stack",
            "visualDirection": brand_profile.visual_direction if brand_profile else "modern, premium, clear",
            "tokens": DESIGN_TOKENS,
        },
        "selectedSlides": [_map_source_slide(slide) for slide in selected_slides],
        "subjectContext": {
            "deckType": payload.deckType or "unknown",
            "audience": payload.audience or deck.audience,
            "selectedSubject": selected_subject,
            "detectedSubjects": detected_subjects,
            "actionId": payload.actionId,
            "actionPrompt": payload.actionPrompt,
            "userPrompt": payload.userPrompt or payload.prompt,
            "latestBatchId": payload.latestBatchId,
        },
        "audienceContext": audience_context,
        "slideArchetypeContext": archetype_context,
        "knowledgeMetadata": knowledge_metadata,
        "runtimeContext": runtime_context,
        "runtimeCapabilities": runtime_capabilities,
        "sourceFactPackage": source_fact_package,
        "artifactContext": prompt_context_artifact,
        "retrievalContext": retrieval_context,
        "userInstruction": payload.prompt,
        "styleId": payload.styleId,
        "brandProductId": payload.brandProductId,
        "additionalContext": payload.additionalContext,
        "rules": [
            "Return one generated slide for each selected source slide.",
            "Do not edit the uploaded PDF directly.",
            "Use render_schema_json only; do not return HTML, Svelte, or executable JavaScript.",
            "Keep all element bounds inside a 1920x1080 canvas.",
            "Use subjectContext to classify the slide topic before rewriting it.",
            "Use audienceContext to tune language, evidence density, and decision criteria for the VC persona.",
            "Use slideArchetypeContext to preserve the expected pitch-deck narrative arc and slide job.",
            "Use runtimeContext to keep deck objects, field usage, rebuild jobs, and review surfaces aligned with the repository model.",
            "Use runtimeCapabilities to select the right LLM task, guardrail group, and missing-evidence behavior before responding.",
            "Use sourceFactPackage as the only factual claim source and flag missing evidence instead of inventing stronger claims.",
        ],
    }


def _map_variation_job(job: ElementVariationJob) -> dict:
    return {
        "id": job.id,
        "deckId": job.deck_id,
        "workspaceId": job.workspace_id,
        "generatedSlideId": job.generated_slide_id,
        "elementId": job.element_id,
        "baseElementVersionId": job.base_element_version_id,
        "instruction": job.instruction,
        "variationCount": job.variation_count,
        "status": job.status,
        "outputElementVersionId": job.output_element_version_id,
        "errorMessage": job.error_message,
        "createdAt": _iso(job.created_at) or "",
        "startedAt": _iso(job.started_at),
        "completedAt": _iso(job.completed_at),
    }


def _latest_element_version(element: GeneratedSlideElement) -> GeneratedSlideElementVersion | None:
    if not element.versions:
        return None
    return sorted(element.versions, key=lambda item: item.version_number, reverse=True)[0]


def _next_element_version_number(element: GeneratedSlideElement) -> int:
    latest = _latest_element_version(element)
    return (latest.version_number + 1) if latest else 1


def _create_deterministic_element_variation(
    element: GeneratedSlideElement,
    *,
    instruction: str,
) -> tuple[dict, dict, dict]:
    content = dict(element.content_json or {})
    style = dict(element.style_json or {})
    position = {
        "x": element.x,
        "y": element.y,
        "width": element.width,
        "height": element.height,
        "rotation": element.rotation,
    }

    if element.element_type == "text":
        base_text = str(content.get("text") or "")
        content["text"] = f"{base_text} ({instruction.strip()})"[:500]
    elif element.element_type == "shape":
        style["variationInstruction"] = instruction.strip()
    else:
        content["variationInstruction"] = instruction.strip()

    return content, style, position


def _apply_element_to_render_schema(slide: GeneratedSlide, element: GeneratedSlideElement) -> None:
    render_schema = RenderSchema.model_validate(slide.render_schema_json).model_dump()
    for render_element in render_schema["elements"]:
        if render_element.get("id") != element.element_key:
            continue
        render_element["x"] = element.x
        render_element["y"] = element.y
        render_element["width"] = element.width
        render_element["height"] = element.height
        content = element.content_json or {}
        style = element.style_json or {}
        if "text" in content:
            render_element["text"] = content.get("text")
        if "analyticsKey" in content:
            render_element["analyticsKey"] = content.get("analyticsKey")
        for key in ["fontSize", "fontWeight", "colorToken", "fillToken", "assetUrl"]:
            if key in style:
                render_element[key] = style[key]
        break
    slide.render_schema_json = RenderSchema.model_validate(render_schema).model_dump()


def _render_schema_with_element_variation(
    render_schema_json: dict,
    element: GeneratedSlideElement,
    content: dict,
    style: dict,
    position: dict,
) -> dict:
    render_schema = RenderSchema.model_validate(render_schema_json).model_dump()
    for render_element in render_schema["elements"]:
        if render_element.get("id") != element.element_key:
            continue
        render_element["x"] = int(position.get("x", element.x))
        render_element["y"] = int(position.get("y", element.y))
        render_element["width"] = int(position.get("width", element.width))
        render_element["height"] = int(position.get("height", element.height))
        if "text" in content:
            render_element["text"] = content.get("text")
        if "analyticsKey" in content:
            render_element["analyticsKey"] = content.get("analyticsKey")
        for key in ["fontSize", "fontWeight", "colorToken", "fillToken", "assetUrl"]:
            if key in style:
                render_element[key] = style[key]
        break
    return RenderSchema.model_validate(render_schema).model_dump()


def _record_llm_artifact(
    db: Session,
    *,
    deck_id: str,
    artifact_type: str,
    artifact_key: str,
    summary: str,
    payload_json: dict,
    metrics_json: dict | None = None,
    store_payload: bool = True,
) -> DeckLlmArtifact:
    artifact_id = generate_id("artifact")
    stored_payload = _write_json_artifact_to_storage(db, deck_id, artifact_id, payload_json) if store_payload else payload_json
    stored_metrics = dict(metrics_json or {})
    if store_payload:
        stored_metrics.update(
            {
                "artifactStorageProvider": stored_payload.get("storageProvider"),
                "artifactStoragePath": stored_payload.get("storagePath"),
            }
        )
    canonical_payload = persist_canonical_llm_artifact(
        db,
        deck_id=deck_id,
        artifact_type=artifact_type,
        payload=payload_json,
    )
    if canonical_payload:
        stored_metrics.update(
            {
                "canonicalArtifactFilename": canonical_payload["filename"],
                "canonicalArtifactStoragePath": canonical_payload["storagePath"],
            }
        )
        if isinstance(stored_payload, dict):
            stored_payload = {
                **stored_payload,
                "canonicalFilename": canonical_payload["filename"],
                "canonicalStoragePath": canonical_payload["storagePath"],
            }
    artifact = DeckLlmArtifact(
        id=artifact_id,
        deck_id=deck_id,
        extraction_run_id=None,
        artifact_type=artifact_type,
        artifact_key=artifact_key,
        schema_version=SMART_DECK_ARTIFACT_SCHEMA_VERSION,
        status="ready",
        summary=summary,
        payload_json=stored_payload,
        bucket_payload_key=stored_payload.get("storagePath") if isinstance(stored_payload, dict) else None,
        metrics_json=stored_metrics,
    )
    db.add(artifact)
    return artifact


def _storage_user_id_for_deck(db: Session, deck_id: str) -> str:
    user_id = db.query(Deck.user_id).filter(Deck.id == deck_id).scalar()
    return user_id or "unknown-user"


def _write_json_artifact_to_storage(db: Session, deck_id: str, artifact_key: str, payload: dict) -> dict:
    bucket_service = get_bucket_artifact_service()
    user_id = _storage_user_id_for_deck(db, deck_id)
    storage_path = bucket_service.make_llm_artifact_key(user_id=user_id, deck_id=deck_id, artifact_id=artifact_key)
    bucket_service.put_json_sync(key=storage_path, data=payload)
    return {
        "artifactStorageVersion": SMART_DECK_ASSISTANT_ARTIFACT_STORAGE_VERSION,
        "storageProvider": settings.upload_storage_backend,
        "storagePath": storage_path,
        "contentType": "application/json",
    }


def _json_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


def _write_render_schema_json_artifact(
    *,
    user_id: str | None,
    deck_id: str,
    design_version_id: str,
    generated_slide_id: str,
    code_version_id: str,
    render_schema: dict,
) -> dict:
    bucket_service = get_bucket_artifact_service()
    storage_user_id = user_id or "unknown-user"
    storage_path = bucket_service.make_render_schema_key(
        user_id=storage_user_id,
        deck_id=deck_id,
        design_version_id=design_version_id,
        generated_slide_id=generated_slide_id,
        code_version_id=code_version_id,
    )
    bucket_service.put_json_sync(key=storage_path, data=render_schema)
    return {
        "storageProvider": settings.upload_storage_backend,
        "storagePath": storage_path,
        "contentType": "application/json",
        "renderSchemaHash": _json_hash(render_schema),
    }


def _write_code_metadata_json_artifact(
    *,
    user_id: str | None,
    deck_id: str,
    design_version_id: str,
    generated_slide_id: str,
    code_version_id: str,
    code_json: dict,
) -> dict:
    bucket_service = get_bucket_artifact_service()
    storage_user_id = user_id or "unknown-user"
    storage_path = bucket_service.make_code_key(
        user_id=storage_user_id,
        deck_id=deck_id,
        design_version_id=design_version_id,
        generated_slide_id=generated_slide_id,
        code_version_id=code_version_id,
    )
    bucket_service.put_json_sync(key=storage_path, data=code_json)
    return {
        "storageProvider": settings.upload_storage_backend,
        "storagePath": storage_path,
        "contentType": "application/json",
        "codeJsonHash": _json_hash(code_json),
    }


def _write_design_version_manifest_json_artifact(
    *,
    user_id: str | None,
    deck_id: str,
    design_version_id: str,
    manifest_json: dict,
) -> dict:
    bucket_service = get_bucket_artifact_service()
    storage_user_id = user_id or "unknown-user"
    storage_path = bucket_service.make_manifest_key(
        user_id=storage_user_id,
        deck_id=deck_id,
        design_version_id=design_version_id,
    )
    bucket_service.put_json_sync(key=storage_path, data=manifest_json)
    return {
        "storageProvider": settings.upload_storage_backend,
        "storagePath": storage_path,
        "contentType": "application/json",
        "manifestHash": _json_hash(manifest_json),
    }


def load_deck_llm_artifact_payload(artifact: DeckLlmArtifact) -> dict:
    payload = artifact.payload_json or {}
    if not isinstance(payload, dict):
        return {}
    if payload.get("artifactStorageVersion") != SMART_DECK_ASSISTANT_ARTIFACT_STORAGE_VERSION:
        return payload

    storage_path = payload.get("storagePath")
    if not isinstance(storage_path, str):
        return {}
    try:
        payload_bytes = get_bucket_artifact_service().get_bytes_sync(key=storage_path)
    except Exception:
        return {}
    return json.loads(payload_bytes.decode("utf-8"))


def _fit_text(value: str, max_length: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 1].rstrip() + "..."


def _build_render_schema(slide: DeckSlide, prompt: str) -> dict:
    title = _fit_text(slide.title or f"Slide {_source_slide_number(slide)}", 80)
    body_source = slide.summary or slide.narrative_notes or slide.raw_text or prompt
    body = _fit_text(body_source, 220)
    eyebrow = _fit_text(prompt, 92)
    schema = {
        "schemaVersion": "smart-deck-render-schema.v1",
        "width": 1920,
        "height": 1080,
        "background": {
            "type": "layered",
            "fill": "brand.surface",
            "layers": [
                {
                    "id": "bg_surface",
                    "type": "shape",
                    "shape": "rectangle",
                    "role": "base_surface",
                    "x": 0,
                    "y": 0,
                    "width": 1920,
                    "height": 1080,
                    "zIndex": 0,
                    "style": {"fill": "brand.surface", "opacity": 1, "radius": 0},
                },
                {
                    "id": "bg_accent_orb",
                    "type": "shape",
                    "shape": "circle",
                    "role": "brand_accent",
                    "x": 1380,
                    "y": -220,
                    "width": 680,
                    "height": 680,
                    "zIndex": 0,
                    "style": {"fill": "brand.accent", "opacity": 0.16, "radius": 999},
                },
            ],
        },
        "brandTokensUsed": ["brand.surface", "brand.accent", "brand.heading", "brand.body"],
        "analytics": {
            "slidePurpose": slide.semantic_slide_type or slide.role or "generated_slide",
            "audience": "smart_deck_generation",
            "trackedEvents": ["slide_view", "slide_time_spent", "element_click"],
        },
        "exportMetadata": {
            "exportReady": True,
            "renderer": "smart_deck_scene_graph",
            "supportedFormats": ["digital", "preview_image"],
        },
        "elements": [
            {
                "id": "el_eyebrow",
                "type": "text",
                "text": eyebrow,
                "x": 160,
                "y": 132,
                "width": 980,
                "height": 54,
                "zIndex": 30,
                "fontSize": 28,
                "fontWeight": "600",
                "colorToken": "brand.accent",
                "analyticsKey": "eyebrow",
            },
            {
                "id": "el_title",
                "type": "text",
                "text": title,
                "x": 160,
                "y": 230,
                "width": 1080,
                "height": 210,
                "zIndex": 31,
                "fontSize": 82,
                "fontWeight": "700",
                "colorToken": "brand.heading",
                "analyticsKey": "headline",
            },
            {
                "id": "el_body",
                "type": "text",
                "text": body,
                "x": 166,
                "y": 505,
                "width": 960,
                "height": 210,
                "zIndex": 32,
                "fontSize": 34,
                "fontWeight": "400",
                "colorToken": "brand.body",
                "analyticsKey": "body",
            },
            {
                "id": "el_rule",
                "type": "shape",
                "x": 160,
                "y": 804,
                "width": 520,
                "height": 8,
                "zIndex": 21,
                "fillToken": "brand.accent",
                "analyticsKey": "accent_rule",
            },
        ],
    }
    return RenderSchema.model_validate(schema).model_dump()


def _extract_json_payload(raw_text: str) -> dict:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response did not contain a JSON object.")
    return json.loads(text[start : end + 1])


def _build_anthropic_prompt(llm_context: dict) -> str:
    return (
        "You are the Deck AI Stack Smart Deck slide design engine.\n"
        "Return JSON only. Do not return markdown, HTML, Svelte, JavaScript, or base64 assets.\n"
        "Return exactly one generated slide for each selectedSlides item and preserve each sourceSlideId.\n"
        "Each renderSchema must match smart-deck-render-schema.v1 with a 1920x1080 canvas, "
        "a background, brandTokensUsed, analytics, exportMetadata, and bounded elements.\n"
        "Use only approved tokens: brand.surface, brand.surfaceAlt, brand.heading, brand.body, brand.accent, brand.muted.\n"
        "Use layered backgrounds when possible. Do not use external asset URLs or data URLs.\n\n"
        "Audience intelligence:\n"
        "- Use audienceContext.matchedPersona to write for the specific VC role.\n"
        "- Use subjectContext.selectedSubject and detectedSubjects to classify the selected slide before rewriting it.\n"
        "- Use slideArchetypeContext.inferredArchetypes and recommendedSequence to match the slide's narrative job.\n"
        "- Use slideArchetypeContext.knowledgeModules.render_schema_rules before choosing layout and element structure.\n"
        "- Use slideArchetypeContext.knowledgeModules.deck_recipes to keep generated slides aligned with deck stage and sequence.\n"
        "- Use slideArchetypeContext.knowledgeModules.generation_contracts to populate analytics sourceFactsUsed, assumptions, missingInputs, qualityWarnings, and confidence.\n"
        "- Use slideArchetypeContext.knowledgeModules.diagnostics to avoid unsupported traction, regulatory, return, customer, and investor claims.\n"
        "- Use slideArchetypeContext.knowledgeModules.writing_rules before writing headlines, captions, and proof points.\n"
        "- Use slideArchetypeContext.knowledgeModules.quality_rubrics to self-check the slide before returning JSON.\n"
        "- Use slideArchetypeContext.knowledgeModules.hallucination_constraints as hard limits on unsupported facts.\n"
        "- Use sourceFactPackage.facts as the only allowed source for factual claims.\n"
        "- Populate analytics.sourceFactIds with sourceFactPackage fact IDs such as fact_1.\n"
        "- Populate analytics.sourceFactsUsed with short readable labels or excerpts for those same fact IDs.\n"
        "- Respect sourceFactPackage factType, evidenceStrength, and safetyFlags.\n"
        "- Do not strengthen facts marked do_not_strengthen; treat financial, regulatory, customer, and metric facts carefully.\n"
        "- If sourceFactPackage lacks a needed fact, populate analytics.missingInputs or analytics.qualityWarnings instead of inventing it.\n"
        "- Convert generic founder language into investor decision language only when source facts support it.\n"
        "- Emphasize market, traction, unit economics, competition, team, raise, and risk according to the selected slide.\n"
        "- Preserve factual claims exactly unless the context supplies stronger evidence.\n"
        "- If evidence is missing, keep language conservative rather than fabricating metrics or benchmarks.\n\n"
        "Required output shape:\n"
        "{\"designVersionName\":\"string\",\"slides\":[{\"sourceSlideId\":\"string\","
        "\"slideNumber\":1,\"title\":\"string\",\"renderSchema\":{\"schemaVersion\":"
        "\"smart-deck-render-schema.v1\",\"width\":1920,\"height\":1080,\"background\":"
        "{\"type\":\"layered\",\"fill\":\"brand.surface\",\"layers\":[]},"
        "\"brandTokensUsed\":[\"brand.surface\",\"brand.heading\"],"
        "\"analytics\":{\"slidePurpose\":\"string\",\"audience\":\"string\","
        "\"sourceFactIds\":[\"fact_1\"],\"sourceFactsUsed\":[\"source-backed fact\"],\"assumptions\":[],"
        "\"missingInputs\":[],\"qualityWarnings\":[],\"confidence\":0.8,"
        "\"trackedEvents\":[\"slide_view\"]},"
        "\"exportMetadata\":{\"exportReady\":true,\"renderer\":\"smart_deck_scene_graph\","
        "\"supportedFormats\":[\"digital\",\"preview_image\"]},\"elements\":[]}}]}\n\n"
        f"Smart Deck context:\n{json.dumps(llm_context, ensure_ascii=True)}"
    )


def _call_anthropic_render_payload(llm_context: dict, model: str, api_key: str) -> dict:
    response_payload = call_anthropic_message(
        api_key=api_key,
        model=model,
        max_tokens=settings.anthropic_max_tokens,
        system="You output only valid JSON for a backend-validated slide render schema.",
        user=_build_anthropic_prompt(llm_context),
        timeout=90,
    )
    return _extract_json_payload(extract_anthropic_text(response_payload))


def _call_openai_render_payload(llm_context: dict, model: str, api_key: str) -> dict:
    response_payload = call_openai_response(
        api_key=api_key,
        model=model,
        system="You output only valid JSON for a backend-validated slide render schema.",
        user=_build_anthropic_prompt(llm_context),
        timeout=90,
        response_format={"type": "json_object"},
    )
    return _extract_json_payload(extract_openai_text(response_payload))


def _call_openrouter_render_payload(llm_context: dict, model: str, api_key: str) -> dict:
    response_payload = call_openrouter_chat_completion(
        api_key=api_key,
        model=model,
        system="You output only valid JSON for a backend-validated slide render schema.",
        user=_build_anthropic_prompt(llm_context),
        timeout=90,
        response_format={"type": "json_object"},
    )
    return _extract_json_payload(extract_openrouter_text(response_payload))


def _validate_generated_render_payload(render_payload: dict, selected_slides: list[DeckSlide]) -> dict[str, dict]:
    expected_ids = [slide.id for slide in selected_slides]
    slides_payload = render_payload.get("slides")
    if not isinstance(slides_payload, list):
        raise ValueError("LLM response must include a slides array.")
    if len(slides_payload) != len(expected_ids):
        raise ValueError("LLM response slide count must match selectedSourceSlideIds.")

    by_source_id: dict[str, dict] = {}
    for slide_payload in slides_payload:
        if not isinstance(slide_payload, dict):
            raise ValueError("Each generated slide payload must be an object.")
        source_slide_id = slide_payload.get("sourceSlideId")
        if source_slide_id not in expected_ids:
            raise ValueError(f"LLM response included an unselected source slide: {source_slide_id}")
        if source_slide_id in by_source_id:
            raise ValueError(f"LLM response duplicated source slide: {source_slide_id}")
        render_schema = RenderSchema.model_validate(slide_payload.get("renderSchema")).model_dump()
        by_source_id[source_slide_id] = {
            "sourceSlideId": source_slide_id,
            "slideNumber": int(slide_payload.get("slideNumber") or 0),
            "title": str(slide_payload.get("title") or "Generated slide"),
            "renderSchema": render_schema,
        }

    missing_ids = [slide_id for slide_id in expected_ids if slide_id not in by_source_id]
    if missing_ids:
        raise ValueError(f"LLM response omitted selected source slides: {', '.join(missing_ids)}")
    return by_source_id


def _build_generation_plan(llm_context: dict, selected_slides: list[DeckSlide]) -> dict:
    archetype_context = llm_context.get("slideArchetypeContext") if isinstance(llm_context.get("slideArchetypeContext"), dict) else {}
    inferred_archetypes = archetype_context.get("inferredArchetypes") if isinstance(archetype_context.get("inferredArchetypes"), list) else []
    primary_archetype = inferred_archetypes[0] if inferred_archetypes else {}
    knowledge_metadata = llm_context.get("knowledgeMetadata") if isinstance(llm_context.get("knowledgeMetadata"), dict) else {}
    source_fact_package = llm_context.get("sourceFactPackage") if isinstance(llm_context.get("sourceFactPackage"), dict) else {}
    return {
        "schemaVersion": "smart-deck-generation-plan.v1",
        "knowledgeMetadata": knowledge_metadata,
        "runtimeContext": llm_context.get("runtimeContext") if isinstance(llm_context.get("runtimeContext"), dict) else {},
        "sourceFactSummary": {
            "schemaVersion": source_fact_package.get("schemaVersion"),
            "factCount": source_fact_package.get("factCount") or 0,
            "coverage": source_fact_package.get("coverage") or {},
        },
        "selectedSlideCount": len(selected_slides),
        "recommendedSequence": archetype_context.get("recommendedSequence") or [],
        "primaryArchetype": {
            "slug": primary_archetype.get("slug"),
            "description": primary_archetype.get("description"),
            "requiredInputs": primary_archetype.get("requiredInputs") or [],
            "renderContract": primary_archetype.get("renderContract") or {},
            "outputContract": primary_archetype.get("outputContract") or {},
        },
        "steps": [
            {
                "id": "classify",
                "instruction": "Classify each selected slide by narrative job before generating.",
            },
            {
                "id": "retrieve",
                "instruction": "Use sourceFactPackage, audience context, deck recipe, diagnostics, writing rules, and hallucination constraints.",
            },
            {
                "id": "draft",
                "instruction": "Return render_schema_json only, with analytics for source facts, assumptions, missing inputs, quality warnings, and confidence.",
            },
            {
                "id": "critique",
                "instruction": "Check unsupported claims, missing evidence, sequence fit, visual density, and render-schema validity.",
            },
            {
                "id": "repair",
                "instruction": "If critique status is review, make one bounded repair pass and validate again before persistence.",
            },
            {
                "id": "persist",
                "instruction": "Persist final validated render schema, artifacts, telemetry, model, provider, and knowledge version.",
            },
        ],
    }


def _critique_generated_render_payload(
    generated_by_source_id: dict[str, dict],
    generation_plan: dict,
    source_fact_package: dict | None = None,
) -> dict:
    slide_critiques = []
    warning_count = 0
    missing_input_count = 0
    allowed_fact_ids: set[str] = set()
    fact_by_id: dict[str, dict] = {}
    allowed_fact_texts = []
    if isinstance(source_fact_package, dict):
        fact_by_id = {
            str(fact.get("id")): fact
            for fact in source_fact_package.get("facts", [])
            if isinstance(fact, dict) and fact.get("id")
        }
        allowed_fact_ids = {
            *fact_by_id.keys()
        }
        allowed_fact_texts = [
            _normalise_fact_text(fact.get("text")).lower()
            for fact in source_fact_package.get("facts", [])
            if isinstance(fact, dict) and _normalise_fact_text(fact.get("text"))
        ]
    for source_slide_id, generated_payload in generated_by_source_id.items():
        render_schema = generated_payload.get("renderSchema") if isinstance(generated_payload.get("renderSchema"), dict) else {}
        analytics = render_schema.get("analytics") if isinstance(render_schema.get("analytics"), dict) else {}
        source_fact_ids = analytics.get("sourceFactIds") if isinstance(analytics.get("sourceFactIds"), list) else []
        source_facts = analytics.get("sourceFactsUsed") if isinstance(analytics.get("sourceFactsUsed"), list) else []
        missing_inputs = analytics.get("missingInputs") if isinstance(analytics.get("missingInputs"), list) else []
        quality_warnings = analytics.get("qualityWarnings") if isinstance(analytics.get("qualityWarnings"), list) else []
        assumptions = analytics.get("assumptions") if isinstance(analytics.get("assumptions"), list) else []
        confidence = analytics.get("confidence")
        warnings = list(quality_warnings)
        unsupported_fact_ids = [
            str(fact_id)
            for fact_id in source_fact_ids
            if str(fact_id) not in allowed_fact_ids
        ]
        if allowed_fact_ids and not source_fact_ids:
            warnings.append("No fact IDs were declared in renderSchema.analytics.sourceFactIds.")
        if unsupported_fact_ids:
            warnings.append("Some analytics.sourceFactIds entries do not exist in sourceFactPackage facts.")
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
        if "requires_source" in cited_safety_flags and not source_facts:
            warnings.append("Cited facts require source labels in analytics.sourceFactsUsed.")
        if not source_facts:
            warnings.append("No source facts were declared in renderSchema.analytics.sourceFactsUsed.")
        unsupported_facts = []
        for fact in source_facts:
            fact_text = _normalise_fact_text(fact).lower()
            if not fact_text:
                continue
            if allowed_fact_texts and not any(fact_text in allowed or allowed in fact_text for allowed in allowed_fact_texts):
                unsupported_facts.append(str(fact))
        if unsupported_facts:
            warnings.append("Some analytics.sourceFactsUsed entries do not match sourceFactPackage facts.")
        try:
            confidence_value = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence_value = None
            warnings.append("Confidence value is not numeric.")
        if assumptions and confidence_value is not None and confidence_value > 0.85:
            warnings.append("High confidence with declared assumptions should be reviewed.")
        critique_decision = build_critique_decision(
            warnings=warnings,
            missing_inputs=missing_inputs,
            unsupported_fact_ids=unsupported_fact_ids,
            unsupported_facts=unsupported_facts,
            cited_safety_flags=cited_safety_flags,
        )
        warning_count += len(warnings)
        missing_input_count += len(missing_inputs)
        slide_critiques.append(
            {
                "sourceSlideId": source_slide_id,
                "generatedTitle": generated_payload.get("title"),
                "status": critique_decision.get("status") if critique_decision.get("status") != "blocking" else "review",
                "sourceFactIds": [str(fact_id) for fact_id in source_fact_ids],
                "sourceFactCount": len(source_facts),
                "assumptionCount": len(assumptions),
                "missingInputs": missing_inputs,
                "warnings": warnings,
                "unsupportedSourceFactIds": unsupported_fact_ids,
                "unsupportedSourceFacts": unsupported_facts,
                "citedFactTypes": cited_fact_types,
                "citedSafetyFlags": cited_safety_flags,
                "confidence": confidence_value,
                "decision": critique_decision,
                "dimensions": critique_decision.get("dimensions") or [],
                "repairActions": critique_decision.get("repairActions") or [],
            }
        )
    critique_summary = summarize_critique_decisions(
        [slide.get("decision") or {} for slide in slide_critiques]
    )
    return {
        "schemaVersion": "smart-deck-generation-critique.v1",
        "knowledgeMetadata": generation_plan.get("knowledgeMetadata") or {},
        "status": critique_summary.get("status") if critique_summary.get("status") != "blocking" else "review",
        "warningCount": warning_count,
        "missingInputCount": missing_input_count,
        "decision": critique_summary,
        "dimensions": [
            dimension
            for slide in slide_critiques
            for dimension in (slide.get("dimensions") or [])
        ][:50],
        "repairActions": critique_summary.get("repairActions") or [],
        "allowedSourceFactIds": sorted(allowed_fact_ids),
        "sourceFactCoverage": (source_fact_package or {}).get("coverage") if isinstance(source_fact_package, dict) else {},
        "slides": slide_critiques,
    }


def _build_repair_context(llm_context: dict, render_payload: dict, generation_critique: dict) -> dict:
    return {
        **llm_context,
        "repairContext": {
            "schemaVersion": "smart-deck-generation-repair-context.v1",
            "instruction": (
                "Repair the previous Smart Deck render payload. Return the same output shape with the same "
                "sourceSlideId values. Fix only the issues listed in critique. Do not add unsupported facts. "
                "If evidence is still missing, keep the claim conservative and populate analytics.missingInputs "
                "or analytics.qualityWarnings instead of inventing data."
            ),
            "sourceFactPackage": llm_context.get("sourceFactPackage") if isinstance(llm_context.get("sourceFactPackage"), dict) else {},
            "originalRenderPayload": render_payload,
            "critique": generation_critique,
            "repairActions": generation_critique.get("repairActions") or [],
        },
    }


def _repair_render_payload(
    provider: str,
    llm_context: dict,
    render_payload: dict,
    generation_critique: dict,
    selected_slides: list[DeckSlide],
    prompt: str,
    model: str | None,
    api_key: str | None,
) -> tuple[dict, dict[str, dict], dict, dict]:
    repair_context = _build_repair_context(llm_context, render_payload, generation_critique)
    repaired_payload = _generate_render_payload(
        provider,
        repair_context,
        selected_slides,
        prompt,
        model,
        api_key,
    )
    repaired_by_source_id = _validate_generated_render_payload(repaired_payload, selected_slides)
    repaired_critique = _critique_generated_render_payload(
        repaired_by_source_id,
        llm_context.get("generationPlan") or {},
        llm_context.get("sourceFactPackage") if isinstance(llm_context.get("sourceFactPackage"), dict) else {},
    )
    repair_artifact_payload = {
        "schemaVersion": "smart-deck-generation-repair.v1",
        "knowledgeMetadata": (llm_context.get("knowledgeMetadata") if isinstance(llm_context.get("knowledgeMetadata"), dict) else {}),
        "status": "completed",
        "originalCritique": generation_critique,
        "repairedCritique": repaired_critique,
        "originalDesignVersionName": render_payload.get("designVersionName"),
        "repairedDesignVersionName": repaired_payload.get("designVersionName"),
        "repairedSlideCount": len(repaired_payload.get("slides") or []),
    }
    return repaired_payload, repaired_by_source_id, repaired_critique, repair_artifact_payload


def _generate_render_payload(
    provider: str,
    llm_context: dict,
    selected_slides: list[DeckSlide],
    prompt: str,
    model: str | None,
    api_key: str | None,
) -> dict:
    if provider == "anthropic":
        if not model or not api_key:
            raise ValueError("Claude generation requires a resolved model and API key.")
        return _call_anthropic_render_payload(llm_context, model, api_key)
    if provider == "openai":
        if not model or not api_key:
            raise ValueError("OpenAI generation requires a resolved model and API key.")
        return _call_openai_render_payload(llm_context, model, api_key)
    if provider == "openrouter":
        if not model or not api_key:
            raise ValueError("OpenRouter generation requires a resolved model and API key.")
        return _call_openrouter_render_payload(llm_context, model, api_key)
    if provider == "deterministic":
        return _build_deterministic_render_payload(selected_slides, prompt)
    raise ValueError("Smart Deck generation requires a workspace AI key, OPENAI_API_KEY, OPENROUTER_API_KEY, or ANTHROPIC_API_KEY.")


def get_smart_deck_workspace(db: Session, deck_id: str) -> dict | None:
    deck = _load_deck(db, deck_id)
    if deck is None:
        return None
    runtime_context = build_architecture_runtime_context()
    runtime_capabilities = build_smart_deck_runtime_capabilities()

    workspace, preference = _ensure_workspace_state(db, deck)
    db.flush()
    source_slides = sorted(deck.slides, key=lambda item: item.slide_index)
    jobs = sorted(deck.generation_jobs, key=lambda item: item.created_at, reverse=True)
    versions = sorted(deck.design_versions, key=lambda item: item.created_at, reverse=True)
    active_version = next(
        (
            version
            for version in versions
            if version.id == deck.current_design_version_id and version.status != "discarded"
        ),
        None,
    )
    if active_version is None:
        active_version = next(
            (
                version
                for version in versions
                if version.id == workspace.active_design_version_id and version.status != "discarded"
            ),
            None,
        )
    if active_version is None:
        active_version = next((version for version in versions if version.is_active), None)
    if active_version is None:
        active_version = next((version for version in versions if version.status != "discarded"), None)
    active_generated = sorted(active_version.generated_slides, key=lambda item: item.slide_number) if active_version else []
    if active_version and workspace.active_design_version_id != active_version.id:
        workspace.active_design_version_id = active_version.id
    if active_generated and workspace.active_generated_slide_id is None:
        workspace.active_generated_slide_id = active_generated[0].id
    if source_slides and workspace.active_source_slide_id is None:
        workspace.active_source_slide_id = source_slides[0].id
    if preference.active_design_version_id is None and workspace.active_design_version_id:
        preference.active_design_version_id = workspace.active_design_version_id
    if preference.active_generated_slide_id is None and workspace.active_generated_slide_id:
        preference.active_generated_slide_id = workspace.active_generated_slide_id
    if preference.active_source_slide_id is None and workspace.active_source_slide_id:
        preference.active_source_slide_id = workspace.active_source_slide_id
    if preference.selected_element_id is None and workspace.selected_element_id:
        preference.selected_element_id = workspace.selected_element_id
    if preference.audience is None:
        preference.audience = deck.audience
    if preference.deck_type is None:
        preference.deck_type = "vc_fund_pitch" if deck.audience and any(marker in deck.audience.lower() for marker in ("lp", "fund", "partner")) else "startup_pitch"
    if preference.preferred_model is None:
        preference.preferred_model = settings.anthropic_model
    if preference.selected_subject is None and source_slides:
        preference.selected_subject = source_slides[0].role
    db.commit()
    messages = (
        db.query(SmartDeckMessage)
        .filter(SmartDeckMessage.workspace_id == workspace.id)
        .order_by(SmartDeckMessage.created_at.asc())
        .all()
    )
    design_tokens = db.query(DesignToken).filter(DesignToken.deck_id == deck.id).order_by(DesignToken.created_at.desc()).all()

    mapped_versions = [_map_design_version(version) for version in versions]
    mapped_generated_slides = [_map_generated_slide(slide) for slide in active_generated]
    return {
        "deck": {
            "id": deck.id,
            "workspaceId": deck.workspace_id,
            "title": deck.title,
            "audience": deck.audience,
            "purpose": deck.purpose,
            "status": deck.status,
            "summary": deck.summary,
        },
        "workspace": _map_workspace_state(workspace),
        "preferences": _map_preference(preference),
        "messages": [_map_message(message) for message in messages],
        "designTokens": [_map_design_token(token) for token in design_tokens],
        "sourceSlides": [_map_source_slide(slide) for slide in source_slides],
        "generationJobs": [_map_job(job) for job in jobs],
        "designVersions": mapped_versions,
        "activeDesignVersionId": active_version.id if active_version else None,
        "activeSourceSlideId": workspace.active_source_slide_id,
        "activeGeneratedSlideId": workspace.active_generated_slide_id,
        "generatedSlides": mapped_generated_slides,
        "deck_id": deck.id,
        "current_design_version_id": active_version.id if active_version else None,
        "current_batch_id": active_version.id if active_version else None,
        "slides": [_map_product_spine_slide(slide) for slide in active_generated],
        "design_versions": [_map_product_spine_design_version(version) for version in versions],
        "knowledgeMetadata": build_llm_knowledge_metadata(),
        "runtimeContext": runtime_context,
        "runtimeCapabilities": runtime_capabilities,
    }


def create_generation_job(
    db: Session,
    deck_id: str,
    payload: CreateSmartDeckGenerationJobInput,
    *,
    run_id: str | None = None,
) -> tuple[dict, dict, dict] | None:
    deck = _load_deck(db, deck_id)
    if deck is None:
        return None
    workspace, preference = _ensure_workspace_state(db, deck)

    slide_lookup = {slide.id: slide for slide in deck.slides}
    missing_ids = [slide_id for slide_id in payload.selectedSourceSlideIds if slide_id not in slide_lookup]
    if missing_ids:
        raise ValueError(f"Selected source slides do not belong to this deck: {', '.join(missing_ids)}")

    selected_slides = [slide_lookup[slide_id] for slide_id in payload.selectedSourceSlideIds]
    selected_slides.sort(key=lambda item: item.slide_index)
    now = datetime.utcnow()
    preferred_model = payload.preferredModel or preference.preferred_model
    claude_config = _resolve_claude_config(db, deck, preferred_model)
    provider = claude_config["provider"]
    resolved_model = claude_config["model"]
    audience_profile = _load_audience_profile(db, deck.audience)
    llm_context = _build_llm_context(deck, selected_slides, payload, audience_profile)
    knowledge_metadata = llm_context.get("knowledgeMetadata") or {}
    source_fact_package = llm_context.get("sourceFactPackage") if isinstance(llm_context.get("sourceFactPackage"), dict) else {}
    generation_plan = _build_generation_plan(llm_context, selected_slides)
    llm_context["generationPlan"] = generation_plan
    job = None
    if run_id:
        job = db.query(GenerationJob).filter(GenerationJob.id == run_id, GenerationJob.deck_id == deck.id).first()
    if job is None:
        job = GenerationJob(
            id=run_id or generate_id("genjob"),
            deck_id=deck.id,
            status="queued",
            provider="provider_pending",
            model=None,
            prompt=payload.prompt,
            selected_source_slide_ids_json=payload.selectedSourceSlideIds,
            style_id=payload.styleId,
            brand_product_id=payload.brandProductId,
            additional_context=payload.additionalContext,
            llm_context_json=None,
        )
        db.add(job)
    job.deck_id = deck.id
    job.status = "running"
    job.provider = provider
    job.model = resolved_model if provider in {"anthropic", "openai", "openrouter"} else None
    job.prompt = payload.prompt
    job.selected_source_slide_ids_json = payload.selectedSourceSlideIds
    job.style_id = payload.styleId
    job.brand_product_id = payload.brandProductId
    job.additional_context = payload.additionalContext
    existing_workflow_context = job.llm_context_json if isinstance(job.llm_context_json, dict) else {}
    job.llm_context_json = {
        **existing_workflow_context,
        **llm_context,
        "llmProvider": {
            "provider": provider,
            "model": resolved_model if provider in {"anthropic", "openai", "openrouter"} else None,
            "credentialSource": claude_config.get("source"),
        },
    }
    job.result_json = None
    job.error_message = None
    job.completed_at = None
    workspace.status = "generating"
    workspace.active_source_slide_id = payload.selectedSourceSlideIds[0]
    preference.selected_source_slide_ids_json = payload.selectedSourceSlideIds
    preference.active_source_slide_id = payload.selectedSourceSlideIds[0]
    if payload.audience is not None:
        preference.audience = payload.audience
    if payload.deckType is not None:
        preference.deck_type = payload.deckType
    if payload.preferredModel is not None:
        preference.preferred_model = payload.preferredModel
    if payload.selectedSubject is not None:
        preference.selected_subject = payload.selectedSubject
    if payload.actionId is not None:
        preference.selected_action_id = payload.actionId
    _record_smart_deck_message(
        db,
        workspace_id=workspace.id,
        deck_id=deck.id,
        role="user",
        content=payload.prompt,
        generation_job_id=job.id,
        selected_source_slide_ids=payload.selectedSourceSlideIds,
        metadata_json={"styleId": payload.styleId, "brandProductId": payload.brandProductId},
    )
    db.flush()
    record_agent_event(
        db,
        event_name="ai.smart_deck_generation.started",
        run_type="smart_deck_generation",
        workspace_id=workspace.id,
        deck_id=deck.id,
        user_id=deck.user_id,
        run_id=job.id,
        status="running",
        provider=provider,
        model=job.model,
        metadata={
            "selectedSlideCount": len(selected_slides),
            "styleId": payload.styleId,
            "brandProductId": payload.brandProductId,
            "promptLength": len(payload.prompt),
            "hasAdditionalContext": bool(payload.additionalContext),
            "credentialSource": claude_config.get("source"),
            "knowledgeVersion": knowledge_metadata.get("version"),
            "knowledgeSource": knowledge_metadata.get("source"),
            "runtimeContextVersion": (llm_context.get("runtimeContext") or {}).get("schemaVersion"),
        },
    )

    try:
        _record_llm_artifact(
            db,
            deck_id=deck.id,
            artifact_type="smart_deck_generation_plan",
            artifact_key=job.id,
            summary=f"Knowledge-aware generation plan for Smart Deck job {job.id}.",
            payload_json=generation_plan,
            metrics_json={
                "selectedSlideCount": len(selected_slides),
                "knowledgeVersion": knowledge_metadata.get("version"),
                "knowledgeSource": knowledge_metadata.get("source"),
                "runtimeContextVersion": (llm_context.get("runtimeContext") or {}).get("schemaVersion"),
            },
        )
        _record_llm_artifact(
            db,
            deck_id=deck.id,
            artifact_type="smart_deck_source_facts",
            artifact_key=job.id,
            summary=f"Source fact package for Smart Deck job {job.id}.",
            payload_json=source_fact_package,
            metrics_json={
                "factCount": source_fact_package.get("factCount"),
                "factTypeCounts": source_fact_package.get("factTypeCounts"),
                "safetyFlagCounts": source_fact_package.get("safetyFlagCounts"),
                "selectedSlideCount": len(selected_slides),
                "missingSlideFactCount": len((source_fact_package.get("coverage") or {}).get("missingSlideFactIds") or []),
                "knowledgeVersion": knowledge_metadata.get("version"),
                "knowledgeSource": knowledge_metadata.get("source"),
                "runtimeContextVersion": (llm_context.get("runtimeContext") or {}).get("schemaVersion"),
            },
        )
        version = DesignVersion(
            id=generate_id("designver"),
            deck_id=deck.id,
            generation_job_id=job.id,
            name=f"Smart Deck redesign {now.strftime('%Y-%m-%d %H:%M')}",
            status="preview",
            is_active=False,
            summary=f"Generated {len(selected_slides)} slide design(s) from selected source slides.",
        )
        db.add(version)
        db.flush()

        _record_llm_artifact(
            db,
            deck_id=deck.id,
            artifact_type="smart_deck_generation_context",
            artifact_key=job.id,
            summary=f"LLM context for Smart Deck generation job {job.id}.",
            payload_json=llm_context,
            metrics_json={
                "selectedSlideCount": len(selected_slides),
                "hasArtifactContext": bool(llm_context.get("artifactContext")),
                "promptLength": len(payload.prompt),
                "provider": provider,
                "model": resolved_model if provider in {"anthropic", "openai", "openrouter"} else None,
                "credentialSource": claude_config.get("source"),
                "knowledgeVersion": knowledge_metadata.get("version"),
                "knowledgeSource": knowledge_metadata.get("source"),
                "runtimeContextVersion": (llm_context.get("runtimeContext") or {}).get("schemaVersion"),
            },
        )

        render_payload = _generate_render_payload(
            provider,
            llm_context,
            selected_slides,
            payload.prompt,
            resolved_model,
            claude_config.get("apiKey"),
        )
        generated_by_source_id = _validate_generated_render_payload(render_payload, selected_slides)
        generation_critique = _critique_generated_render_payload(generated_by_source_id, generation_plan, source_fact_package)
        repair_performed = False
        repair_artifact_payload: dict | None = None
        final_critique = generation_critique
        final_render_payload = render_payload
        _record_llm_artifact(
            db,
            deck_id=deck.id,
            artifact_type="smart_deck_generation_critique",
            artifact_key=job.id,
            summary=f"Knowledge-aware critique for Smart Deck job {job.id}.",
            payload_json=generation_critique,
            metrics_json={
                "status": generation_critique.get("status"),
                "warningCount": generation_critique.get("warningCount"),
                "missingInputCount": generation_critique.get("missingInputCount"),
                "blockingCount": (generation_critique.get("decision") or {}).get("blockingCount"),
                "repairActionCount": len(generation_critique.get("repairActions") or []),
                "knowledgeVersion": knowledge_metadata.get("version"),
                "knowledgeSource": knowledge_metadata.get("source"),
                "runtimeContextVersion": (llm_context.get("runtimeContext") or {}).get("schemaVersion"),
            },
        )
        if generation_critique.get("status") == "review":
            (
                final_render_payload,
                generated_by_source_id,
                final_critique,
                repair_artifact_payload,
            ) = _repair_render_payload(
                provider,
                llm_context,
                render_payload,
                generation_critique,
                selected_slides,
                payload.prompt,
                resolved_model,
                claude_config.get("apiKey"),
            )
            repair_performed = True
            _record_llm_artifact(
                db,
                deck_id=deck.id,
                artifact_type="smart_deck_generation_repair",
                artifact_key=job.id,
                summary=f"Bounded repair pass for Smart Deck job {job.id}.",
                payload_json=repair_artifact_payload,
                metrics_json={
                    "status": repair_artifact_payload.get("status"),
                    "originalCritiqueStatus": generation_critique.get("status"),
                    "repairedCritiqueStatus": final_critique.get("status"),
                    "repairedWarningCount": final_critique.get("warningCount"),
                    "repairedMissingInputCount": final_critique.get("missingInputCount"),
                    "repairedBlockingCount": (final_critique.get("decision") or {}).get("blockingCount"),
                    "repairedRepairActionCount": len(final_critique.get("repairActions") or []),
                    "knowledgeVersion": knowledge_metadata.get("version"),
                    "knowledgeSource": knowledge_metadata.get("source"),
                },
            )

        if isinstance(final_render_payload.get("designVersionName"), str) and final_render_payload["designVersionName"].strip():
            version.name = final_render_payload["designVersionName"].strip()[:255]

        created_slide_ids: list[str] = []
        candidate_slide_versions: list[dict] = []
        for slide in selected_slides:
            generated_payload = generated_by_source_id[slide.id]
            render_schema = generated_payload["renderSchema"]
            generated_slide = GeneratedSlide(
                id=generate_id("genslide"),
                deck_id=deck.id,
                design_version_id=version.id,
                generation_job_id=job.id,
                source_slide_id=slide.id,
                slide_number=_source_slide_number(slide),
                title=generated_payload["title"],
                status="ready",
                render_schema_json=render_schema,
                design_tokens_json=DESIGN_TOKENS,
                preview_image_url=None,
                validation_status="valid",
            )
            db.add(generated_slide)
            db.flush()
            created_slide_ids.append(generated_slide.id)
            _record_design_tokens(
                db,
                deck_id=deck.id,
                design_version_id=version.id,
                generated_slide_id=generated_slide.id,
            )
            code_version_id = generate_id("codever")
            render_schema_artifact = _write_render_schema_json_artifact(
                user_id=deck.user_id,
                deck_id=deck.id,
                design_version_id=version.id,
                generated_slide_id=generated_slide.id,
                code_version_id=code_version_id,
                render_schema=render_schema,
            )
            code_json = {
                "renderer": "GeneratedSlideRenderer",
                "source": "render_schema_json",
                "lifecycle": "candidate",
                "state": "candidate",
                "renderSchemaHash": render_schema_artifact["renderSchemaHash"],
                "renderSchemaStorageProvider": render_schema_artifact["storageProvider"],
                "renderSchemaStoragePath": render_schema_artifact["storagePath"],
                "bucketRenderSchemaKey": render_schema_artifact["storagePath"],
                "provider": provider,
                "model": job.model,
                "knowledgeMetadata": knowledge_metadata,
                "sourceSlideId": slide.id,
                "designVersionId": version.id,
                "generationJobId": job.id,
            }
            code_metadata_artifact = _write_code_metadata_json_artifact(
                user_id=deck.user_id,
                deck_id=deck.id,
                design_version_id=version.id,
                generated_slide_id=generated_slide.id,
                code_version_id=code_version_id,
                code_json=code_json,
            )
            code_json = {
                **code_json,
                "codeJsonHash": code_metadata_artifact["codeJsonHash"],
                "codeJsonStorageProvider": code_metadata_artifact["storageProvider"],
                "codeJsonStoragePath": code_metadata_artifact["storagePath"],
                "bucketCodeJsonKey": code_metadata_artifact["storagePath"],
            }
            code_version = GeneratedSlideCodeVersion(
                id=code_version_id,
                generated_slide_id=generated_slide.id,
                version_number=1,
                code_kind="render_schema",
                schema_version="smart-deck-render-schema.v1",
                render_schema_json=render_schema,
                code_json=code_json,
                bucket_render_schema_key=render_schema_artifact["storagePath"],
                bucket_code_key=code_metadata_artifact["storagePath"],
                bucket_thumbnail_key=None,
                status="valid",
                validation_errors_json=[],
            )
            db.add(code_version)
            db.flush()
            generated_elements = _persist_generated_slide_elements(
                db,
                deck_id=deck.id,
                design_version_id=version.id,
                generated_slide=generated_slide,
                source_slide_id=slide.id,
                render_schema=render_schema,
            )
            _record_llm_artifact(
                db,
                deck_id=deck.id,
                artifact_type="generated_slide_render_schema",
                artifact_key=generated_slide.id,
                summary=f"Validated render schema for generated slide {generated_slide.id}.",
                payload_json={
                    "generatedSlideId": generated_slide.id,
                    "sourceSlideId": slide.id,
                    "designVersionId": version.id,
                    "generationJobId": job.id,
                    "codeVersionId": code_version.id,
                    "renderSchema": render_schema,
                    "renderSchemaHash": render_schema_artifact["renderSchemaHash"],
                    "bucketRenderSchemaKey": render_schema_artifact["storagePath"],
                    "designTokens": DESIGN_TOKENS,
                    "knowledgeMetadata": knowledge_metadata,
                    "generatedSlideElementIds": [element.id for element in generated_elements],
                },
                metrics_json={
                    "elementCount": len(render_schema.get("elements", [])),
                    "persistedElementCount": len(generated_elements),
                    "slideNumber": generated_slide.slide_number,
                },
            )
            _record_llm_artifact(
                db,
                deck_id=deck.id,
                artifact_type="generated_slide_code_version",
                artifact_key=code_version.id,
                summary=f"Generated slide code version {code_version.id}.",
                payload_json={
                    "generatedSlideId": generated_slide.id,
                    "codeVersionId": code_version.id,
                    "codeKind": code_version.code_kind,
                    "schemaVersion": code_version.schema_version,
                    "renderSchema": render_schema,
                    "renderSchemaHash": render_schema_artifact["renderSchemaHash"],
                    "bucketRenderSchemaKey": render_schema_artifact["storagePath"],
                    "codeJson": code_version.code_json,
                },
                metrics_json={
                    "validationErrorCount": 0,
                    "versionNumber": code_version.version_number,
                },
            )
            candidate_slide_versions.append(
                {
                    "generated_slide_id": generated_slide.id,
                    "code_version_id": code_version.id,
                    "render_schema_json": render_schema,
                    "render_schema_hash": render_schema_artifact["renderSchemaHash"],
                    "bucket_render_schema_key": render_schema_artifact["storagePath"],
                    "bucket_code_key": code_metadata_artifact["storagePath"],
                    "source_slide_id": slide.id,
                    "state": "candidate",
                }
            )

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.result_json = {
            "designVersionId": version.id,
            "state": "preview",
            "generatedSlideIds": created_slide_ids,
            "candidateSlideVersions": candidate_slide_versions,
        }
        workspace.status = "reviewing"
        workspace.active_design_version_id = version.id
        workspace.active_generated_slide_id = created_slide_ids[0] if created_slide_ids else None
        preference.active_design_version_id = version.id
        preference.active_generated_slide_id = workspace.active_generated_slide_id
        _record_smart_deck_message(
            db,
            workspace_id=workspace.id,
            deck_id=deck.id,
            role="assistant",
            content=f"Created design version {version.id} with {len(created_slide_ids)} generated slide(s).",
            generation_job_id=job.id,
            selected_source_slide_ids=payload.selectedSourceSlideIds,
            metadata_json={"designVersionId": version.id, "generatedSlideIds": created_slide_ids},
        )
        manifest_payload = {
            "deck_id": deck.id,
            "design_version_id": version.id,
            "designVersionId": version.id,
            "state": "preview",
            "generationJobId": job.id,
            "generatedSlideIds": created_slide_ids,
            "slides": [
                {
                    "generated_slide_id": candidate["generated_slide_id"],
                    "code_version_id": candidate["code_version_id"],
                    "render_schema_key": candidate["bucket_render_schema_key"],
                    "code_key": candidate["bucket_code_key"],
                }
                for candidate in candidate_slide_versions
            ],
            "candidateSlideVersions": candidate_slide_versions,
            "selectedSourceSlideIds": payload.selectedSourceSlideIds,
            "provider": provider,
            "model": job.model,
            "credentialSource": claude_config.get("source"),
            "knowledgeMetadata": knowledge_metadata,
            "sourceFactsArtifactType": "smart_deck_source_facts",
            "generationPlanArtifactType": "smart_deck_generation_plan",
            "generationCritiqueArtifactType": "smart_deck_generation_critique",
            "generationRepairArtifactType": "smart_deck_generation_repair" if repair_performed else None,
        }
        manifest_artifact = _write_design_version_manifest_json_artifact(
            user_id=deck.user_id,
            deck_id=deck.id,
            design_version_id=version.id,
            manifest_json=manifest_payload,
        )
        version.bucket_manifest_key = manifest_artifact["storagePath"]
        manifest_payload = {
            **manifest_payload,
            "bucketManifestKey": manifest_artifact["storagePath"],
            "manifestHash": manifest_artifact["manifestHash"],
        }
        _record_llm_artifact(
            db,
            deck_id=deck.id,
            artifact_type="smart_deck_design_version_manifest",
            artifact_key=version.id,
            summary=f"Manifest for Smart Deck design version {version.id}.",
            payload_json=manifest_payload,
            metrics_json={
                "generatedSlideCount": len(created_slide_ids),
                "selectedSlideCount": len(payload.selectedSourceSlideIds),
                "sourceFactCount": source_fact_package.get("factCount"),
                "sourceFactTypeCounts": source_fact_package.get("factTypeCounts"),
                "sourceFactSafetyFlagCounts": source_fact_package.get("safetyFlagCounts"),
                "missingSlideFactCount": len((source_fact_package.get("coverage") or {}).get("missingSlideFactIds") or []),
                "critiqueStatus": final_critique.get("status"),
                "critiqueWarningCount": final_critique.get("warningCount"),
                "critiqueMissingInputCount": final_critique.get("missingInputCount"),
                "critiqueBlockingCount": (final_critique.get("decision") or {}).get("blockingCount"),
                "repairActionCount": len(final_critique.get("repairActions") or []),
                "repairPerformed": repair_performed,
            },
        )
        record_agent_event(
            db,
            event_name="ai.smart_deck_generation.completed",
            run_type="smart_deck_generation",
            workspace_id=workspace.id,
            deck_id=deck.id,
            user_id=deck.user_id,
            run_id=job.id,
            status="completed",
            provider=provider,
            model=job.model,
            metadata={
                "designVersionId": version.id,
                "generatedSlideCount": len(created_slide_ids),
                "selectedSlideCount": len(payload.selectedSourceSlideIds),
                "credentialSource": claude_config.get("source"),
                "knowledgeVersion": knowledge_metadata.get("version"),
                "knowledgeSource": knowledge_metadata.get("source"),
                "runtimeContextVersion": (llm_context.get("runtimeContext") or {}).get("schemaVersion"),
                "sourceFactCount": source_fact_package.get("factCount"),
                "sourceFactTypeCounts": source_fact_package.get("factTypeCounts"),
                "sourceFactSafetyFlagCounts": source_fact_package.get("safetyFlagCounts"),
                "missingSlideFactCount": len((source_fact_package.get("coverage") or {}).get("missingSlideFactIds") or []),
                "critiqueStatus": final_critique.get("status"),
                "critiqueWarningCount": final_critique.get("warningCount"),
                "critiqueMissingInputCount": final_critique.get("missingInputCount"),
                "critiqueBlockingCount": (final_critique.get("decision") or {}).get("blockingCount"),
                "repairActionCount": len(final_critique.get("repairActions") or []),
                "repairPerformed": repair_performed,
            },
        )
        db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = datetime.utcnow()
        workspace.status = "failed"
        _record_smart_deck_message(
            db,
            workspace_id=workspace.id,
            deck_id=deck.id,
            role="system",
            content=f"Generation failed: {exc}",
            generation_job_id=job.id,
            selected_source_slide_ids=payload.selectedSourceSlideIds,
        )
        record_agent_event(
            db,
            event_name="ai.smart_deck_generation.failed",
            run_type="smart_deck_generation",
            workspace_id=workspace.id,
            deck_id=deck.id,
            user_id=deck.user_id,
            run_id=job.id,
            event_level="error",
            status="failed",
            provider=provider,
            model=job.model,
            error_category=exc.__class__.__name__,
            error_message=str(exc),
            metadata={
                "selectedSlideCount": len(payload.selectedSourceSlideIds),
                "promptLength": len(payload.prompt),
                "hasAdditionalContext": bool(payload.additionalContext),
                "credentialSource": claude_config.get("source"),
                "knowledgeVersion": knowledge_metadata.get("version"),
                "knowledgeSource": knowledge_metadata.get("source"),
                "runtimeContextVersion": (llm_context.get("runtimeContext") or {}).get("schemaVersion"),
            },
        )
        db.commit()
        raise

    workspace = get_smart_deck_workspace(db, deck_id)
    if workspace is None:
        raise ValueError("Smart Deck workspace could not be reloaded.")

    reloaded_job = db.query(GenerationJob).filter(GenerationJob.id == job.id).one()
    reloaded_version = (
        db.query(DesignVersion)
        .options(selectinload(DesignVersion.generated_slides).selectinload(GeneratedSlide.code_versions))
        .filter(DesignVersion.id == version.id)
        .one()
    )
    return _map_job(reloaded_job), _map_design_version(reloaded_version), workspace


def get_generation_job(db: Session, deck_id: str, job_id: str) -> dict | None:
    job = db.query(GenerationJob).filter(GenerationJob.deck_id == deck_id, GenerationJob.id == job_id).first()
    return _map_job(job) if job else None


def get_slide_redesign_run(db: Session, run_id: str) -> dict | None:
    job = (
        db.query(GenerationJob)
        .options(
            selectinload(GenerationJob.design_versions).selectinload(DesignVersion.generated_slides).selectinload(GeneratedSlide.code_versions),
            selectinload(GenerationJob.generated_slides),
        )
        .filter(GenerationJob.id == run_id)
        .first()
    )
    if job is None:
        return None

    result_json = job.result_json if isinstance(job.result_json, dict) else {}
    generated_version_ids = result_json.get("generatedSlideIds")
    if not isinstance(generated_version_ids, list):
        generated_version_ids = [slide.id for slide in job.generated_slides]

    design_version_id = result_json.get("designVersionId")
    design_version = None
    if isinstance(design_version_id, str):
        design_version = next((version for version in job.design_versions if version.id == design_version_id), None)
    if design_version is None and job.design_versions:
        design_version = sorted(job.design_versions, key=lambda item: item.created_at, reverse=True)[0]

    mapped_design_version = _map_design_version(design_version) if design_version else None
    generated_slides = [
        {
            "generated_slide_id": slide.get("generated_slide_id") or slide.get("id"),
            "code_version_id": slide.get("current_version_id"),
            "render_schema_json": slide.get("render_schema_json") or slide.get("renderSchema") or {},
            "bucket_render_schema_key": slide.get("bucket_render_schema_key"),
            "bucket_code_key": slide.get("bucket_code_key"),
            "bucket_artifacts": slide.get("bucket_artifacts") or {},
        }
        for slide in (mapped_design_version or {}).get("generatedSlides", [])
    ]
    runtime_capabilities = build_smart_deck_runtime_capabilities()
    return {
        "runId": job.id,
        "run_id": job.id,
        "deckId": job.deck_id,
        "deck_id": job.deck_id,
        "status": job.status,
        "intentType": "redesign_slides",
        "outputMode": "editable_slide_versions",
        "scope": "selected_slides",
        "selectedSlideIds": job.selected_source_slide_ids_json or [],
        "batchId": design_version.id if design_version else design_version_id,
        "design_version_id": design_version.id if design_version else design_version_id,
        "state": (mapped_design_version or {}).get("state") or ("preview" if design_version else None),
        "changed_slide_ids": (mapped_design_version or {}).get("changed_slide_ids") or [],
        "generated_slides": generated_slides,
        "generatedVersionIds": generated_version_ids,
        "generatedVersionCount": len(generated_version_ids),
        "generationJob": _map_job(job),
        "designVersion": mapped_design_version,
        "errorMessage": job.error_message,
    }


def list_design_versions(db: Session, deck_id: str) -> dict | None:
    deck = _load_deck(db, deck_id)
    if deck is None:
        return None
    versions = sorted(deck.design_versions, key=lambda item: item.created_at, reverse=True)
    active = next((version for version in versions if version.is_active), None)
    return {
        "designVersions": [_map_design_version(version) for version in versions],
        "activeDesignVersionId": active.id if active else None,
    }


def apply_design_version(db: Session, deck_id: str, version_id: str) -> dict | None:
    version = (
        db.query(DesignVersion)
        .options(
            selectinload(DesignVersion.generated_slides).selectinload(GeneratedSlide.code_versions),
            selectinload(DesignVersion.generated_slides)
            .selectinload(GeneratedSlide.elements)
            .selectinload(GeneratedSlideElement.versions),
        )
        .filter(DesignVersion.deck_id == deck_id, DesignVersion.id == version_id)
        .first()
    )
    if version is None:
        return None
    now = datetime.utcnow()
    for candidate in (
        db.query(DesignVersion)
        .options(
            selectinload(DesignVersion.generated_slides).selectinload(GeneratedSlide.code_versions),
            selectinload(DesignVersion.generated_slides)
            .selectinload(GeneratedSlide.elements)
            .selectinload(GeneratedSlideElement.versions),
        )
        .filter(DesignVersion.deck_id == deck_id)
        .all()
    ):
        candidate.is_active = candidate.id == version.id
        if candidate.id == version.id:
            candidate.status = "applied"
            candidate.applied_at = now
            for slide in candidate.generated_slides:
                latest_code = _latest_code_version(slide)
                if latest_code:
                    slide.current_version_id = latest_code.id
                    slide.render_schema_json = latest_code.render_schema_json
                    _set_code_version_lifecycle(latest_code, "accepted")
                for element in slide.elements:
                    for element_version in element.versions:
                        if element_version.status == "candidate":
                            element_version.status = "accepted"
        elif candidate.status in {"applied", "restored"}:
            candidate.status = "draft"
            for slide in candidate.generated_slides:
                latest_code = _latest_code_version(slide)
                if latest_code:
                    _set_code_version_lifecycle(latest_code, "superseded")
    workspace = db.query(SmartDeckWorkspace).filter(SmartDeckWorkspace.deck_id == deck_id).first()
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if deck:
        deck.current_design_version_id = version.id
    if workspace:
        active_slides = sorted(version.generated_slides, key=lambda item: item.slide_number)
        workspace.status = "ready"
        workspace.active_design_version_id = version.id
        workspace.active_generated_slide_id = active_slides[0].id if active_slides else None
        preference = db.query(SmartDeckPreference).filter(SmartDeckPreference.workspace_id == workspace.id).first()
        if preference:
            preference.active_design_version_id = version.id
            preference.active_generated_slide_id = workspace.active_generated_slide_id
    _record_design_version_snapshot_artifact(db, deck_id, version, "apply")
    db.flush()
    _rewrite_design_version_manifest(db, version, "saved", "apply")
    apply_retention(db, deck_id)
    db.commit()
    return list_design_versions(db, deck_id)


def discard_design_version(db: Session, deck_id: str, version_id: str) -> dict | None:
    version = (
        db.query(DesignVersion)
        .options(
            selectinload(DesignVersion.generated_slides).selectinload(GeneratedSlide.code_versions),
            selectinload(DesignVersion.generated_slides)
            .selectinload(GeneratedSlide.elements)
            .selectinload(GeneratedSlideElement.versions),
        )
        .filter(DesignVersion.deck_id == deck_id, DesignVersion.id == version_id)
        .first()
    )
    if version is None:
        return None
    for slide in version.generated_slides:
        latest_code = _latest_code_version(slide)
        if latest_code:
            _set_code_version_lifecycle(latest_code, "unused")
        for element in slide.elements:
            for element_version in element.versions:
                if element_version.status == "candidate":
                    element_version.status = "unused"
    version.status = "discarded"
    version.is_active = False
    version.discarded_at = datetime.utcnow()
    workspace = db.query(SmartDeckWorkspace).filter(SmartDeckWorkspace.deck_id == deck_id).first()
    if workspace and workspace.active_design_version_id == version.id:
        next_version = (
            db.query(DesignVersion)
            .filter(
                DesignVersion.deck_id == deck_id,
                DesignVersion.id != version.id,
                DesignVersion.status != "discarded",
            )
            .order_by(DesignVersion.created_at.desc())
            .first()
        )
        next_slides = sorted(next_version.generated_slides, key=lambda item: item.slide_number) if next_version else []
        workspace.active_design_version_id = next_version.id if next_version else None
        workspace.active_generated_slide_id = next_slides[0].id if next_slides else None
        preference = db.query(SmartDeckPreference).filter(SmartDeckPreference.workspace_id == workspace.id).first()
        if preference:
            preference.active_design_version_id = workspace.active_design_version_id
            preference.active_generated_slide_id = workspace.active_generated_slide_id
    db.flush()
    _rewrite_design_version_manifest(db, version, "discarded", "discard")
    apply_retention(db, deck_id)
    db.commit()
    return list_design_versions(db, deck_id)


def restore_design_version(db: Session, deck_id: str, version_id: str) -> dict | None:
    source_version = (
        db.query(DesignVersion)
        .options(
            selectinload(DesignVersion.generated_slides).selectinload(GeneratedSlide.code_versions),
            selectinload(DesignVersion.generated_slides)
            .selectinload(GeneratedSlide.elements)
            .selectinload(GeneratedSlideElement.versions),
        )
        .filter(DesignVersion.deck_id == deck_id, DesignVersion.id == version_id)
        .first()
    )
    if source_version is None:
        return None

    now = datetime.utcnow()
    restore_version = DesignVersion(
        id=generate_id("designver"),
        deck_id=deck_id,
        generation_job_id=source_version.generation_job_id,
        name=f"Restore of {source_version.name}"[:255],
        status="restored",
        is_active=True,
        summary=f"Restored from design version {source_version.id}.",
        created_at=now,
        updated_at=now,
        applied_at=now,
    )
    db.add(restore_version)
    db.flush()

    created_slides: list[GeneratedSlide] = []
    for source_slide in sorted(source_version.generated_slides, key=lambda item: item.slide_number):
        restored_slide = GeneratedSlide(
            id=generate_id("genslide"),
            deck_id=deck_id,
            design_version_id=restore_version.id,
            generation_job_id=source_slide.generation_job_id,
            source_slide_id=source_slide.source_slide_id,
            slide_number=source_slide.slide_number,
            title=source_slide.title,
            status="ready",
            render_schema_json=source_slide.render_schema_json,
            design_tokens_json=source_slide.design_tokens_json,
            preview_image_url=source_slide.preview_image_url,
            validation_status=source_slide.validation_status,
        )
        db.add(restored_slide)
        db.flush()
        created_slides.append(restored_slide)
        source_code = _latest_code_version(source_slide)
        code_version_id = generate_id("codever")
        restored_render_schema = source_code.render_schema_json if source_code else source_slide.render_schema_json
        render_schema_artifact = _write_render_schema_json_artifact(
            user_id=source_version.deck.user_id if source_version.deck else None,
            deck_id=deck_id,
            design_version_id=restore_version.id,
            generated_slide_id=restored_slide.id,
            code_version_id=code_version_id,
            render_schema=restored_render_schema,
        )
        code_json = {
            **(source_code.code_json if source_code and isinstance(source_code.code_json, dict) else {}),
            "sourceDesignVersionId": source_version.id,
            "lifecycle": "accepted",
            "renderSchemaHash": render_schema_artifact["renderSchemaHash"],
            "renderSchemaStorageProvider": render_schema_artifact["storageProvider"],
            "renderSchemaStoragePath": render_schema_artifact["storagePath"],
            "bucketRenderSchemaKey": render_schema_artifact["storagePath"],
        }
        code_metadata_artifact = _write_code_metadata_json_artifact(
            user_id=source_version.deck.user_id if source_version.deck else None,
            deck_id=deck_id,
            design_version_id=restore_version.id,
            generated_slide_id=restored_slide.id,
            code_version_id=code_version_id,
            code_json=code_json,
        )
        code_json = {
            **code_json,
            "codeJsonHash": code_metadata_artifact["codeJsonHash"],
            "codeJsonStorageProvider": code_metadata_artifact["storageProvider"],
            "codeJsonStoragePath": code_metadata_artifact["storagePath"],
            "bucketCodeJsonKey": code_metadata_artifact["storagePath"],
        }
        code_version = GeneratedSlideCodeVersion(
            id=code_version_id,
            generated_slide_id=restored_slide.id,
            version_number=1,
            code_kind=source_code.code_kind if source_code else "render_schema",
            schema_version=source_code.schema_version if source_code else "smart-deck-render-schema.v1",
            render_schema_json=restored_render_schema,
            code_json=code_json,
            bucket_render_schema_key=render_schema_artifact["storagePath"],
            bucket_code_key=code_metadata_artifact["storagePath"],
            bucket_thumbnail_key=None,
            status=source_code.status if source_code else "valid",
            validation_errors_json=source_code.validation_errors_json if source_code else [],
        )
        db.add(code_version)
        restored_slide.current_version_id = code_version.id
        _record_design_tokens(
            db,
            deck_id=deck_id,
            design_version_id=restore_version.id,
            generated_slide_id=restored_slide.id,
        )

    for candidate in (
        db.query(DesignVersion)
        .options(selectinload(DesignVersion.generated_slides).selectinload(GeneratedSlide.code_versions))
        .filter(DesignVersion.deck_id == deck_id, DesignVersion.id != restore_version.id)
        .all()
    ):
        candidate.is_active = False
        if candidate.status in {"applied", "restored"}:
            candidate.status = "draft"
        for slide in candidate.generated_slides:
            latest_code = _latest_code_version(slide)
            if latest_code:
                _set_code_version_lifecycle(latest_code, "superseded")

    workspace = db.query(SmartDeckWorkspace).filter(SmartDeckWorkspace.deck_id == deck_id).first()
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if deck:
        deck.current_design_version_id = restore_version.id
    if workspace:
        workspace.status = "ready"
        workspace.active_design_version_id = restore_version.id
        workspace.active_generated_slide_id = created_slides[0].id if created_slides else None
        preference = db.query(SmartDeckPreference).filter(SmartDeckPreference.workspace_id == workspace.id).first()
        if preference:
            preference.active_design_version_id = restore_version.id
            preference.active_generated_slide_id = workspace.active_generated_slide_id

    db.flush()
    db.refresh(restore_version)
    _record_design_version_snapshot_artifact(db, deck_id, restore_version, "restore")
    db.commit()
    return list_design_versions(db, deck_id)


def get_generated_slide_code(db: Session, deck_id: str, generated_slide_id: str) -> tuple[dict, dict] | None:
    slide = (
        db.query(GeneratedSlide)
        .options(selectinload(GeneratedSlide.code_versions))
        .filter(GeneratedSlide.deck_id == deck_id, GeneratedSlide.id == generated_slide_id)
        .first()
    )
    if slide is None or not slide.code_versions:
        return None
    code_version = _current_code_version(slide) or _latest_code_version(slide)
    if code_version is None:
        return None
    return _map_generated_slide(slide), _map_code_version(code_version)


def get_generated_slide_code_artifact_urls(
    db: Session,
    deck_id: str,
    generated_slide_id: str,
    code_version_id: str,
) -> dict | None:
    code_version = (
        db.query(GeneratedSlideCodeVersion)
        .join(GeneratedSlide, GeneratedSlide.id == GeneratedSlideCodeVersion.generated_slide_id)
        .filter(
            GeneratedSlide.deck_id == deck_id,
            GeneratedSlide.id == generated_slide_id,
            GeneratedSlideCodeVersion.id == code_version_id,
        )
        .first()
    )
    if code_version is None:
        return None

    bucket_service = get_bucket_artifact_service()

    def signed_url(key: str | None) -> str | None:
        if not key:
            return None
        return bucket_service.create_signed_url_sync(key=key)

    return {
        "render_schema_url": signed_url(code_version.bucket_render_schema_key),
        "code_url": signed_url(code_version.bucket_code_key),
        "thumbnail_url": signed_url(code_version.bucket_thumbnail_key),
    }


def save_generated_slide_code_thumbnail(
    db: Session,
    deck_id: str,
    generated_slide_id: str,
    code_version_id: str,
    payload: bytes,
    content_type: str,
) -> dict | None:
    if not payload:
        raise ValueError("Thumbnail payload is required.")
    if len(payload) > 5 * 1024 * 1024:
        raise ValueError("Thumbnail payload must be 5 MB or smaller.")
    if content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError("Thumbnail must be a PNG, JPEG, or WebP image.")

    result = (
        db.query(GeneratedSlideCodeVersion, GeneratedSlide, Deck)
        .join(GeneratedSlide, GeneratedSlide.id == GeneratedSlideCodeVersion.generated_slide_id)
        .join(Deck, Deck.id == GeneratedSlide.deck_id)
        .filter(
            Deck.id == deck_id,
            GeneratedSlide.id == generated_slide_id,
            GeneratedSlideCodeVersion.id == code_version_id,
        )
        .first()
    )
    if result is None:
        return None
    code_version, slide, deck = result
    bucket_service = get_bucket_artifact_service()
    thumbnail_key = bucket_service.make_thumbnail_key(
        user_id=deck.user_id,
        deck_id=deck.id,
        design_version_id=slide.design_version_id,
        generated_slide_id=slide.id,
        code_version_id=code_version.id,
    )
    bucket_service.put_bytes_sync(key=thumbnail_key, data=payload, content_type=content_type)
    code_version.bucket_thumbnail_key = thumbnail_key
    code_json = code_version.code_json if isinstance(code_version.code_json, dict) else {}
    code_version.code_json = {
        **code_json,
        "bucketThumbnailKey": thumbnail_key,
        "thumbnailContentType": content_type,
        "thumbnailUpdatedAt": datetime.utcnow().isoformat() + "Z",
    }
    db.commit()
    return {
        "generated_slide_id": slide.id,
        "code_version_id": code_version.id,
        "bucket_thumbnail_key": thumbnail_key,
        "thumbnail_url": bucket_service.create_signed_url_sync(key=thumbnail_key),
    }


def update_smart_deck_preferences(db: Session, deck_id: str, payload: UpdateSmartDeckPreferenceInput) -> dict | None:
    deck = _load_deck(db, deck_id)
    if deck is None:
        return None
    workspace, preference = _ensure_workspace_state(db, deck)
    source_ids = {slide.id for slide in deck.slides}
    generated_ids = {slide.id for slide in deck.generated_slides}
    version_ids = {version.id for version in deck.design_versions}

    if payload.selectedSourceSlideIds is not None:
        missing_ids = [slide_id for slide_id in payload.selectedSourceSlideIds if slide_id not in source_ids]
        if missing_ids:
            raise ValueError(f"Selected source slides do not belong to this deck: {', '.join(missing_ids)}")
        preference.selected_source_slide_ids_json = payload.selectedSourceSlideIds
    if payload.activeSourceSlideId is not None:
        if payload.activeSourceSlideId not in source_ids:
            raise ValueError("activeSourceSlideId does not belong to this deck.")
        workspace.active_source_slide_id = payload.activeSourceSlideId
        preference.active_source_slide_id = payload.activeSourceSlideId
    if payload.activeDesignVersionId is not None:
        if payload.activeDesignVersionId not in version_ids:
            raise ValueError("activeDesignVersionId does not belong to this deck.")
        workspace.active_design_version_id = payload.activeDesignVersionId
        preference.active_design_version_id = payload.activeDesignVersionId
    if payload.activeGeneratedSlideId is not None:
        if payload.activeGeneratedSlideId not in generated_ids:
            raise ValueError("activeGeneratedSlideId does not belong to this deck.")
        workspace.active_generated_slide_id = payload.activeGeneratedSlideId
        preference.active_generated_slide_id = payload.activeGeneratedSlideId
    if "selectedElementId" in payload.model_fields_set:
        if payload.selectedElementId is None:
            workspace.selected_element_id = None
            preference.selected_element_id = None
        else:
            element = (
                db.query(GeneratedSlideElement)
                .filter(GeneratedSlideElement.deck_id == deck_id, GeneratedSlideElement.id == payload.selectedElementId)
                .first()
            )
            if element is None:
                raise ValueError("selectedElementId does not belong to this deck.")
            workspace.selected_element_id = payload.selectedElementId
            preference.selected_element_id = payload.selectedElementId
    if "audience" in payload.model_fields_set:
        preference.audience = payload.audience
    if "deckType" in payload.model_fields_set:
        preference.deck_type = payload.deckType
    if "preferredModel" in payload.model_fields_set:
        preference.preferred_model = payload.preferredModel
    if "selectedSubject" in payload.model_fields_set:
        preference.selected_subject = payload.selectedSubject
    if "selectedActionId" in payload.model_fields_set:
        preference.selected_action_id = payload.selectedActionId
    if payload.zoomLevel is not None:
        preference.zoom_level = payload.zoomLevel
    if payload.canvasFitMode is not None:
        preference.canvas_fit_mode = payload.canvasFitMode
    if payload.rightPanelOpen is not None:
        preference.right_panel_open = payload.rightPanelOpen
    if payload.slideRailOpen is not None:
        preference.slide_rail_open = payload.slideRailOpen

    db.commit()
    return _map_preference(preference)


def list_smart_deck_messages(db: Session, deck_id: str) -> dict | None:
    deck = _load_deck(db, deck_id)
    if deck is None:
        return None
    workspace, _ = _ensure_workspace_state(db, deck)
    db.commit()
    messages = (
        db.query(SmartDeckMessage)
        .filter(SmartDeckMessage.workspace_id == workspace.id)
        .order_by(SmartDeckMessage.created_at.asc())
        .all()
    )
    return {"messages": [_map_message(message) for message in messages]}


def get_smart_deck_assistant_run(db: Session, run_id: str) -> dict | None:
    artifact = (
        db.query(DeckLlmArtifact)
        .filter(
            DeckLlmArtifact.artifact_type == SMART_DECK_ASSISTANT_ARTIFACT_TYPE,
            DeckLlmArtifact.artifact_key == run_id,
            DeckLlmArtifact.status == "ready",
        )
        .order_by(DeckLlmArtifact.created_at.desc())
        .first()
    )
    if artifact is None:
        return None

    payload = load_deck_llm_artifact_payload(artifact)
    if not payload:
        return None
    insight = payload.get("insight") if isinstance(payload, dict) else None
    assistant_message_ids = (payload.get("messageIds") if isinstance(payload, dict) else {}) or {}
    assistant_message_id = assistant_message_ids.get("assistant") if isinstance(assistant_message_ids, dict) else None
    assistant_message = None
    if assistant_message_id:
        assistant_message = (
            db.query(SmartDeckMessage)
            .filter(SmartDeckMessage.id == assistant_message_id)
            .first()
        )

    if not isinstance(payload, dict):
        return None

    return {
        "runId": payload.get("runId") or run_id,
        "deckId": artifact.deck_id,
        "intentType": payload.get("intentType"),
        "scope": payload.get("scope"),
        "status": "completed",
        "outputType": ASSISTANT_OUTPUT_TYPES.get(payload.get("intentType"), "insight"),
        "provider": payload.get("provider"),
        "model": payload.get("model"),
        "inputContext": payload.get("inputContext") or {},
        "insight": insight or {},
        "assistantMessage": _map_message(assistant_message) if assistant_message is not None else None,
        "savedArtifactId": artifact.id,
    }


def get_generated_slide_scene_graph(db: Session, deck_id: str, generated_slide_id: str) -> dict | None:
    slide = (
        db.query(GeneratedSlide)
        .options(
            selectinload(GeneratedSlide.code_versions),
            selectinload(GeneratedSlide.elements).selectinload(GeneratedSlideElement.versions),
        )
        .filter(GeneratedSlide.deck_id == deck_id, GeneratedSlide.id == generated_slide_id)
        .first()
    )
    if slide is None:
        return None

    elements = sorted(slide.elements, key=lambda item: item.z_index)
    active_versions = [
        latest
        for latest in (_latest_element_version(element) for element in elements)
        if latest is not None
    ]
    return {
        "generatedSlide": _map_generated_slide(slide),
        "elements": [_map_generated_slide_element(element) for element in elements],
        "activeElementVersions": [_map_generated_slide_element_version(version) for version in active_versions],
    }


def update_smart_deck_selection(db: Session, deck_id: str, payload) -> dict | None:
    return update_smart_deck_preferences(
        db,
        deck_id,
        UpdateSmartDeckPreferenceInput(
            activeSourceSlideId=payload.activeSourceSlideId,
            activeGeneratedSlideId=payload.activeGeneratedSlideId,
            selectedElementId=payload.selectedElementId,
        ),
    )


def create_element_variation_job(db: Session, deck_id: str, generated_slide_id: str, element_id: str, payload) -> tuple[dict, dict, dict, dict, dict, dict] | None:
    deck = _load_deck(db, deck_id)
    if deck is None:
        return None
    workspace, preference = _ensure_workspace_state(db, deck)
    slide = (
        db.query(GeneratedSlide)
        .options(
            selectinload(GeneratedSlide.code_versions),
            selectinload(GeneratedSlide.elements).selectinload(GeneratedSlideElement.versions),
            selectinload(GeneratedSlide.source_slide).selectinload(DeckSlide.blocks),
        )
        .filter(GeneratedSlide.deck_id == deck_id, GeneratedSlide.id == generated_slide_id)
        .first()
    )
    if slide is None:
        raise ValueError("generatedSlideId does not belong to this deck.")
    element = next((item for item in slide.elements if item.id == element_id), None)
    if element is None:
        raise ValueError("elementId does not belong to generatedSlideId.")

    base_version = _latest_element_version(element)
    audience_profile = _load_audience_profile(db, deck.audience)
    audience_context = build_vc_prompt_context(
        audience=deck.audience,
        purpose=deck.purpose,
        user_role=deck.workspace.user.role if deck.workspace and deck.workspace.user else None,
        audience_profile=audience_profile,
        deck_metadata=deck.metadata_json,
        brand_evidence=deck.brand_profile.raw_evidence_json if deck.brand_profile else None,
        slide_texts=[slide.source_slide.raw_text if slide.source_slide else ""],
    )
    archetype_context = build_slide_archetype_context(
        audience=deck.audience,
        purpose=deck.purpose,
        slide_texts=[slide.source_slide.raw_text if slide.source_slide else ""],
        slide_titles=[slide.source_slide.title if slide.source_slide else ""],
        slide_roles=[slide.source_slide.role if slide.source_slide else ""],
    )
    retrieval_context = build_element_variation_retrieval_context(
        deck=deck,
        generated_slide=slide,
        element=element,
        instruction=payload.instruction,
        design_tokens=DESIGN_TOKENS,
        audience_context=audience_context,
        archetype_context=archetype_context,
    )
    now = datetime.utcnow()
    preview_version = DesignVersion(
        id=generate_id("designver"),
        deck_id=deck.id,
        generation_job_id=slide.generation_job_id,
        name=f"Element refinement for {slide.title}"[:255],
        status="draft",
        is_active=False,
        summary=f"Candidate element refinement for {slide.title}.",
        created_at=now,
        updated_at=now,
    )
    db.add(preview_version)
    db.flush()

    job = ElementVariationJob(
        id=generate_id("elvar"),
        deck_id=deck.id,
        workspace_id=workspace.id,
        generated_slide_id=slide.id,
        element_id=element.id,
        base_element_version_id=base_version.id if base_version else None,
        user_id=deck.user_id,
        instruction=payload.instruction,
        variation_count=payload.variationCount,
        retrieval_context_json=retrieval_context,
        status="running",
        started_at=now,
    )
    db.add(job)
    db.flush()

    try:
        content, style, position = _create_deterministic_element_variation(element, instruction=payload.instruction)
        base_render_schema = (_current_code_version(slide) or _latest_code_version(slide))
        candidate_render_schema = _render_schema_with_element_variation(
            base_render_schema.render_schema_json if base_render_schema else slide.render_schema_json,
            element,
            content,
            style,
            position,
        )
        candidate_slide = GeneratedSlide(
            id=generate_id("genslide"),
            deck_id=deck.id,
            design_version_id=preview_version.id,
            generation_job_id=slide.generation_job_id,
            source_slide_id=slide.source_slide_id,
            slide_number=slide.slide_number,
            title=slide.title,
            status="ready",
            render_schema_json=candidate_render_schema,
            design_tokens_json=slide.design_tokens_json,
            preview_image_url=slide.preview_image_url,
            validation_status="valid",
        )
        db.add(candidate_slide)
        db.flush()

        selected_candidate_element: GeneratedSlideElement | None = None
        next_version: GeneratedSlideElementVersion | None = None
        for source_element in sorted(slide.elements, key=lambda item: item.z_index):
            is_selected = source_element.id == element.id
            candidate_element = GeneratedSlideElement(
                id=generate_id("gselem"),
                generated_slide_id=candidate_slide.id,
                deck_id=deck.id,
                design_version_id=preview_version.id,
                source_slide_id=source_element.source_slide_id,
                element_key=source_element.element_key,
                element_type=source_element.element_type,
                parent_element_id=source_element.parent_element_id,
                z_index=source_element.z_index,
                x=int(position.get("x", source_element.x)) if is_selected else source_element.x,
                y=int(position.get("y", source_element.y)) if is_selected else source_element.y,
                width=int(position.get("width", source_element.width)) if is_selected else source_element.width,
                height=int(position.get("height", source_element.height)) if is_selected else source_element.height,
                rotation=source_element.rotation,
                locked=source_element.locked,
                visible=source_element.visible,
                style_json=style if is_selected else source_element.style_json,
                content_json=content if is_selected else source_element.content_json,
            )
            db.add(candidate_element)
            db.flush()
            element_version = GeneratedSlideElementVersion(
                id=generate_id("gsever"),
                element_id=candidate_element.id,
                generated_slide_id=candidate_slide.id,
                design_version_id=preview_version.id,
                version_number=1,
                source="element_variation_job" if is_selected else "copied_from_current",
                status="candidate" if is_selected else "active",
                style_json=candidate_element.style_json,
                content_json=candidate_element.content_json,
                change_summary=f"Variation from instruction: {payload.instruction}" if is_selected else "Copied from current slide.",
            )
            db.add(element_version)
            if is_selected:
                selected_candidate_element = candidate_element
                next_version = element_version

        if selected_candidate_element is None or next_version is None:
            raise ValueError("Selected element could not be cloned into preview design version.")

        code_version_id = generate_id("codever")
        render_schema_artifact = _write_render_schema_json_artifact(
            user_id=deck.user_id,
            deck_id=deck.id,
            design_version_id=preview_version.id,
            generated_slide_id=candidate_slide.id,
            code_version_id=code_version_id,
            render_schema=candidate_render_schema,
        )
        code_json = {
            "renderer": "GeneratedSlideRenderer",
            "source": "element_variation_job",
            "lifecycle": "candidate",
            "state": "candidate",
            "baseGeneratedSlideId": slide.id,
            "baseCodeVersionId": base_render_schema.id if base_render_schema else None,
            "baseElementId": element.id,
            "candidateElementId": selected_candidate_element.id,
            "elementVariationJobId": job.id,
            "renderSchemaHash": render_schema_artifact["renderSchemaHash"],
            "renderSchemaStorageProvider": render_schema_artifact["storageProvider"],
            "renderSchemaStoragePath": render_schema_artifact["storagePath"],
            "bucketRenderSchemaKey": render_schema_artifact["storagePath"],
        }
        code_metadata_artifact = _write_code_metadata_json_artifact(
            user_id=deck.user_id,
            deck_id=deck.id,
            design_version_id=preview_version.id,
            generated_slide_id=candidate_slide.id,
            code_version_id=code_version_id,
            code_json=code_json,
        )
        code_version = GeneratedSlideCodeVersion(
            id=code_version_id,
            generated_slide_id=candidate_slide.id,
            version_number=1,
            code_kind="render_schema",
            schema_version="smart-deck-render-schema.v1",
            render_schema_json=candidate_render_schema,
            code_json={
                **code_json,
                "codeJsonHash": code_metadata_artifact["codeJsonHash"],
                "codeJsonStorageProvider": code_metadata_artifact["storageProvider"],
                "codeJsonStoragePath": code_metadata_artifact["storagePath"],
                "bucketCodeJsonKey": code_metadata_artifact["storagePath"],
            },
            bucket_render_schema_key=render_schema_artifact["storagePath"],
            bucket_code_key=code_metadata_artifact["storagePath"],
            bucket_thumbnail_key=None,
            status="valid",
            validation_errors_json=[],
        )
        db.add(code_version)
        candidate_slide.current_version_id = code_version.id
        _record_design_tokens(
            db,
            deck_id=deck.id,
            design_version_id=preview_version.id,
            generated_slide_id=candidate_slide.id,
        )
        job.generated_slide_id = candidate_slide.id
        job.element_id = selected_candidate_element.id
        job.status = "completed"
        job.output_element_version_id = next_version.id
        job.completed_at = datetime.utcnow()
        workspace.status = "reviewing"
        workspace.active_design_version_id = preview_version.id
        workspace.active_generated_slide_id = candidate_slide.id
        workspace.selected_element_id = selected_candidate_element.id
        preference.active_design_version_id = preview_version.id
        preference.active_generated_slide_id = candidate_slide.id
        preference.selected_element_id = selected_candidate_element.id
        db.flush()
        _rewrite_design_version_manifest(db, preview_version, "preview", "element_variation")
        db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = datetime.utcnow()
        db.commit()
        raise

    reloaded_element = (
        db.query(GeneratedSlideElement)
        .options(selectinload(GeneratedSlideElement.versions))
        .filter(GeneratedSlideElement.id == job.element_id)
        .one()
    )
    reloaded_job = db.query(ElementVariationJob).filter(ElementVariationJob.id == job.id).one()
    reloaded_version = (
        db.query(GeneratedSlideElementVersion)
        .filter(GeneratedSlideElementVersion.id == job.output_element_version_id)
        .one()
    )
    reloaded_slide = (
        db.query(GeneratedSlide)
        .options(selectinload(GeneratedSlide.code_versions), selectinload(GeneratedSlide.elements).selectinload(GeneratedSlideElement.versions))
        .filter(GeneratedSlide.id == reloaded_job.generated_slide_id)
        .one()
    )
    reloaded_design_version = (
        db.query(DesignVersion)
        .options(selectinload(DesignVersion.generated_slides).selectinload(GeneratedSlide.code_versions))
        .filter(DesignVersion.id == reloaded_slide.design_version_id)
        .one()
    )
    workspace_payload = get_smart_deck_workspace(db, deck_id)
    return (
        _map_variation_job(reloaded_job),
        _map_generated_slide_element(reloaded_element),
        _map_generated_slide_element_version(reloaded_version),
        _map_generated_slide(reloaded_slide),
        _map_design_version(reloaded_design_version),
        workspace_payload,
    )


def apply_element_version(db: Session, deck_id: str, generated_slide_id: str, element_id: str, version_id: str) -> tuple[dict, dict, dict] | None:
    slide = (
        db.query(GeneratedSlide)
        .options(selectinload(GeneratedSlide.elements).selectinload(GeneratedSlideElement.versions))
        .filter(GeneratedSlide.deck_id == deck_id, GeneratedSlide.id == generated_slide_id)
        .first()
    )
    if slide is None:
        return None
    element = next((item for item in slide.elements if item.id == element_id), None)
    if element is None:
        raise ValueError("elementId does not belong to generatedSlideId.")
    version = next((item for item in element.versions if item.id == version_id), None)
    if version is None:
        raise ValueError("versionId does not belong to elementId.")

    element.content_json = version.content_json
    element.style_json = version.style_json
    position = (version.content_json or {}).get("position") if isinstance(version.content_json, dict) else None
    if isinstance(position, dict):
        element.x = int(position.get("x", element.x))
        element.y = int(position.get("y", element.y))
        element.width = int(position.get("width", element.width))
        element.height = int(position.get("height", element.height))
    version.status = "active"
    for candidate in element.versions:
        if candidate.id != version.id and candidate.status == "active":
            candidate.status = "superseded"
    _apply_element_to_render_schema(slide, element)
    latest_code = sorted(slide.code_versions, key=lambda item: item.version_number, reverse=True)[0] if slide.code_versions else None
    if latest_code is not None:
        latest_code.render_schema_json = slide.render_schema_json
    db.commit()
    return _map_generated_slide_element(element), _map_generated_slide_element_version(version), _map_generated_slide(slide)


def create_smart_deck_message(db: Session, deck_id: str, payload: CreateSmartDeckMessageInput) -> dict | None:
    deck = _load_deck(db, deck_id)
    if deck is None:
        return None
    workspace, _ = _ensure_workspace_state(db, deck)
    source_ids = {slide.id for slide in deck.slides}
    missing_ids = [slide_id for slide_id in payload.selectedSourceSlideIds if slide_id not in source_ids]
    if missing_ids:
        raise ValueError(f"Selected source slides do not belong to this deck: {', '.join(missing_ids)}")
    if payload.generationJobId is not None:
        job = db.query(GenerationJob).filter(GenerationJob.deck_id == deck_id, GenerationJob.id == payload.generationJobId).first()
        if job is None:
            raise ValueError("generationJobId does not belong to this deck.")
    message = _record_smart_deck_message(
        db,
        workspace_id=workspace.id,
        deck_id=deck.id,
        role=payload.role,
        content=payload.content,
        generation_job_id=payload.generationJobId,
        selected_source_slide_ids=payload.selectedSourceSlideIds,
        metadata_json=payload.metadata,
    )
    db.commit()
    return _map_message(message)


def _assistant_slide_summary(slide: DeckSlide) -> dict:
    blocks = sorted(slide.blocks, key=lambda item: item.block_index)
    return {
        "id": slide.id,
        "slideNumber": _source_slide_number(slide),
        "title": slide.title,
        "role": slide.semantic_slide_type or slide.role,
        "summary": _fit_text(slide.summary or slide.raw_text or "", 1200),
        "metricSignals": [
            metric
            for metric in _fit_text(slide.raw_text or "", 1600).replace("\n", " ").split(" ")
            if any(char.isdigit() for char in metric)
        ][:12],
        "blocks": [
            {
                "id": block.id,
                "type": block.block_type,
                "text": _fit_text(block.raw_text or block.normalized_text or "", 240),
            }
            for block in blocks[:10]
        ],
    }


def _assistant_artifact_payloads(deck: Deck) -> dict:
    artifacts: dict[str, dict] = {}
    for artifact in deck.llm_artifacts:
        if artifact.status != "ready" or not artifact.payload_json:
            continue
        if artifact.artifact_type in {"deck_profile", "slide_catalog", "prompt_context"}:
            artifacts[artifact.artifact_type] = load_deck_llm_artifact_payload(artifact)
    prior_insights = [
        {
            "id": artifact.id,
            "artifactKey": artifact.artifact_key,
            "summary": artifact.summary,
            "payload": load_deck_llm_artifact_payload(artifact),
            "createdAt": _iso(artifact.created_at),
        }
        for artifact in sorted(deck.llm_artifacts, key=lambda item: item.created_at, reverse=True)
        if artifact.artifact_type == SMART_DECK_ASSISTANT_ARTIFACT_TYPE and artifact.status == "ready"
    ][:5]
    if prior_insights:
        artifacts["priorAssistantRuns"] = {"runs": prior_insights}
    return artifacts


def _assistant_scope_slides(
    deck: Deck,
    workspace: SmartDeckWorkspace,
    preference: SmartDeckPreference,
    payload: CreateSmartDeckAssistantRunInput,
) -> list[DeckSlide]:
    slide_lookup = {slide.id: slide for slide in deck.slides}
    if payload.scope == "whole_deck":
        return sorted(deck.slides, key=lambda item: item.slide_index)

    if payload.scope == "selected_slides":
        selected_ids = payload.selectedSourceSlideIds
    else:
        selected_ids = [
            payload.activeSourceSlideId
            or preference.active_source_slide_id
            or workspace.active_source_slide_id
            or (preference.selected_source_slide_ids_json or [None])[0]
        ]

    missing_ids = [slide_id for slide_id in selected_ids if slide_id and slide_id not in slide_lookup]
    if missing_ids:
        raise ValueError(f"Selected source slides do not belong to this deck: {', '.join(missing_ids)}")

    selected = [slide_lookup[slide_id] for slide_id in selected_ids if slide_id in slide_lookup]
    selected.sort(key=lambda item: item.slide_index)
    return selected


def _build_assistant_context(
    deck: Deck,
    selected_slides: list[DeckSlide],
    payload: CreateSmartDeckAssistantRunInput,
    audience_profile: dict | None = None,
) -> dict:
    intent = ASSISTANT_INTENTS[payload.intentType]
    active_design_version = next((version for version in deck.design_versions if version.is_active), None)
    brand_profile = deck.brand_profile
    workspace = deck.workspace
    workspace_user = workspace.user if workspace else None
    user_profile = workspace_user.profile if workspace_user else None
    company_profile = workspace.company_profiles[0] if workspace and workspace.company_profiles else None
    target_audience = payload.audience or deck.audience
    audience_context = build_vc_prompt_context(
        audience=target_audience,
        purpose=deck.purpose,
        user_role=workspace_user.role if workspace_user else None,
        audience_profile=audience_profile,
        deck_metadata=deck.metadata_json,
        brand_evidence=brand_profile.raw_evidence_json if brand_profile else None,
        slide_texts=[slide.raw_text or "" for slide in selected_slides],
    )
    archetype_context = build_slide_archetype_context(
        audience=target_audience,
        purpose=deck.purpose,
        slide_texts=[slide.raw_text or "" for slide in selected_slides],
        slide_titles=[slide.title or "" for slide in selected_slides],
        slide_roles=[slide.role or "" for slide in selected_slides],
    )
    runtime_capabilities = build_smart_deck_runtime_capabilities()
    detected_subjects = [
        {
            **detect_smart_deck_subject(slide.title, slide.raw_text, [item for item in [slide.role, slide.semantic_slide_type] if item]),
            "slideId": slide.id,
            "slideTitle": slide.title,
        }
        for slide in selected_slides
    ]
    return {
        "schemaVersion": "smart-deck-assistant-context.v1",
        "intent": {
            "type": payload.intentType,
            "label": intent["label"],
            "template": intent["template"],
        },
        "scope": payload.scope,
        "instruction": payload.instruction,
        "audience": target_audience,
        "audienceContext": audience_context,
        "subjectContext": {
            "deckType": "vc_fund_pitch" if "fund" in (target_audience or "").lower() else "startup_pitch",
            "selectedSubject": payload.intentType,
            "detectedSubjects": detected_subjects,
            "actionId": payload.intentType,
            "actionPrompt": intent["template"],
            "userPrompt": payload.instruction,
            "latestBatchId": active_design_version.id if active_design_version else None,
        },
        "slideArchetypeContext": archetype_context,
        "runtimeCapabilities": runtime_capabilities,
        "deck": {
            "id": deck.id,
            "title": deck.title,
            "audience": deck.audience,
            "purpose": deck.purpose,
            "summary": deck.summary,
            "status": deck.status,
            "slideCount": len(deck.slides),
        },
        "workspace": {
            "id": workspace.id if workspace else None,
            "name": workspace.name if workspace else None,
        },
        "user": {
            "id": workspace_user.id if workspace_user else None,
            "role": workspace_user.role if workspace_user else None,
            "displayName": user_profile.display_name if user_profile else (workspace_user.name if workspace_user else None),
            "headline": user_profile.headline if user_profile else None,
            "jobTitle": user_profile.job_title if user_profile else None,
            "companyName": user_profile.company_name if user_profile else None,
        },
        "company": {
            "canonicalName": company_profile.canonical_name if company_profile else None,
            "websiteUrl": company_profile.website_url if company_profile else None,
            "inferredStage": company_profile.inferred_stage if company_profile else None,
            "founderName": company_profile.founder_name if company_profile else None,
            "teamSummary": company_profile.team_summary if company_profile else None,
        },
        "brand": {
            "companyName": brand_profile.company_name if brand_profile else None,
            "visualDirection": brand_profile.visual_direction if brand_profile else None,
            "industry": (brand_profile.raw_evidence_json or {}).get("industry") if brand_profile else None,
        },
        "selectedSlides": [_assistant_slide_summary(slide) for slide in selected_slides],
        "activeDesignVersion": {
            "id": active_design_version.id,
            "name": active_design_version.name,
            "status": active_design_version.status,
            "generatedSlideCount": len(active_design_version.generated_slides),
        }
        if active_design_version
        else None,
        "artifacts": _assistant_artifact_payloads(deck),
        "rules": [
            "Use saved deck, slide, artifact, brand, and generated-version context before making recommendations.",
            "Use audienceContext.matchedPersona to prioritize the right VC decision criteria and tone.",
            "Use subjectContext to identify the slide topic and apply the corresponding corpus-backed logic.",
            "Use slideArchetypeContext to understand the slide's narrative role and adjacency in the pitch sequence.",
            "Use slideArchetypeContext knowledge modules for deck recipes, diagnostics, generation contracts, writing rules, hallucination constraints, and quality rubrics.",
            "Use runtimeCapabilities from the architecture runtime pack for task routing, guardrails, due diligence gaps, review surfaces, and AI change safety.",
            "Do not invent external market facts; mark assumptions and missing evidence when the deck lacks support.",
            "Call out whether each recommendation helps market conviction, traction proof, unit economics, competition, team credibility, raise logic, or risk reduction.",
            "Return structured JSON only.",
        ],
    }


def _build_anthropic_assistant_prompt(context: dict) -> str:
    return (
        "You are the Deck AI Stack AI assistant for investor deck intelligence.\n"
        "Return JSON only and do not use markdown.\n"
        "Use only the provided context. Do not invent external facts.\n\n"
        "VC audience requirements:\n"
        "- Use audienceContext.matchedPersona as the primary reader model.\n"
        "- Use subjectContext.selectedSubject and detectedSubjects to classify the slide topic.\n"
        "- Make recommendations specific to VC diligence, not generic pitch writing.\n"
        "- Tie observations to market, traction, unit economics, competition, team, raise, or risk.\n"
        "- Preserve source-backed facts and label every unsupported item as an assumption or missingEvidence.\n"
        "- When the user asks for a rewrite, improve specificity and investor usefulness without manufacturing proof.\n\n"
        "Required output shape:\n"
        "{\"title\":\"string\",\"summary\":\"string\",\"content\":{},\"confidence\":\"low|medium|high\","
        "\"assumptions\":[\"string\"],\"missingEvidence\":[\"string\"],"
        "\"suggestedSlideUpdate\":\"string|null\",\"recommendedAction\":\"save_insight|add_to_slide|create_version|none\"}\n\n"
        f"Assistant context:\n{json.dumps(context, ensure_ascii=True)}"
    )


def _call_anthropic_assistant_insight(context: dict, model: str, api_key: str) -> dict:
    response_payload = call_anthropic_message(
        api_key=api_key,
        model=model,
        max_tokens=min(settings.anthropic_max_tokens, 2500),
        system="You output only valid JSON for a backend-validated deck assistant insight.",
        user=_build_anthropic_assistant_prompt(context),
        timeout=60,
    )
    return _extract_json_payload(extract_anthropic_text(response_payload))


def _call_openai_assistant_insight(context: dict, model: str, api_key: str) -> dict:
    response_payload = call_openai_response(
        api_key=api_key,
        model=model,
        system="You output only valid JSON for a backend-validated deck assistant insight.",
        user=_build_anthropic_assistant_prompt(context),
        timeout=60,
        response_format={"type": "json_object"},
    )
    return _extract_json_payload(extract_openai_text(response_payload))


def _call_openrouter_assistant_insight(context: dict, model: str, api_key: str) -> dict:
    response_payload = call_openrouter_chat_completion(
        api_key=api_key,
        model=model,
        system="You output only valid JSON for a backend-validated deck assistant insight.",
        user=_build_anthropic_assistant_prompt(context),
        timeout=60,
        response_format={"type": "json_object"},
    )
    return _extract_json_payload(extract_openrouter_text(response_payload))


def _generate_assistant_insight(provider: str, context: dict, model: str | None, api_key: str | None) -> dict:
    if provider == "anthropic":
        if not model or not api_key:
            raise ValueError("Claude assistant run requires a resolved model and API key.")
        return _call_anthropic_assistant_insight(context, model, api_key)
    if provider == "openai":
        if not model or not api_key:
            raise ValueError("OpenAI assistant run requires a resolved model and API key.")
        return _call_openai_assistant_insight(context, model, api_key)
    if provider == "openrouter":
        if not model or not api_key:
            raise ValueError("OpenRouter assistant run requires a resolved model and API key.")
        return _call_openrouter_assistant_insight(context, model, api_key)
    raise ValueError("Smart Deck assistant runs require a workspace AI key, OPENAI_API_KEY, OPENROUTER_API_KEY, or ANTHROPIC_API_KEY.")


def _validate_assistant_insight(raw: dict, fallback_action: str) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Assistant response must be a JSON object.")
    confidence = raw.get("confidence") if raw.get("confidence") in {"low", "medium", "high"} else "medium"
    action = raw.get("recommendedAction") if raw.get("recommendedAction") in {"save_insight", "add_to_slide", "create_version", "none"} else fallback_action
    return {
        "title": _fit_text(str(raw.get("title") or "Assistant insight"), 140),
        "summary": _fit_text(str(raw.get("summary") or ""), 1200),
        "content": raw.get("content") if isinstance(raw.get("content"), dict) else {},
        "confidence": confidence,
        "assumptions": [str(item)[:500] for item in raw.get("assumptions", []) if str(item).strip()][:12],
        "missingEvidence": [str(item)[:500] for item in raw.get("missingEvidence", []) if str(item).strip()][:12],
        "suggestedSlideUpdate": _fit_text(str(raw["suggestedSlideUpdate"]), 1000)
        if raw.get("suggestedSlideUpdate") is not None
        else None,
        "recommendedAction": action,
    }


def create_smart_deck_assistant_run(
    db: Session,
    deck_id: str,
    payload: CreateSmartDeckAssistantRunInput,
) -> dict | None:
    deck = _load_deck(db, deck_id)
    if deck is None:
        return None
    workspace, preference = _ensure_workspace_state(db, deck)
    selected_slides = _assistant_scope_slides(deck, workspace, preference, payload)
    if not selected_slides:
        raise ValueError("Assistant run requires at least one source slide in scope.")

    run_id = generate_id("sdasst")
    claude_config = _resolve_claude_config(db, deck, preference.preferred_model)
    provider = claude_config["provider"]
    resolved_model = claude_config["model"]
    audience_profile = _load_audience_profile(db, payload.audience or deck.audience)
    context = _build_assistant_context(deck, selected_slides, payload, audience_profile)
    selected_slide_ids = [slide.id for slide in selected_slides]

    user_message = _record_smart_deck_message(
        db,
        workspace_id=workspace.id,
        deck_id=deck.id,
        role="user",
        content=payload.instruction,
        selected_source_slide_ids=selected_slide_ids,
        metadata_json={
            "assistantRunId": run_id,
            "intentType": payload.intentType,
            "scope": payload.scope,
            "audience": payload.audience,
        },
    )
    db.flush()

    raw_insight = _generate_assistant_insight(provider, context, resolved_model, claude_config.get("apiKey"))
    insight = _validate_assistant_insight(raw_insight, ASSISTANT_INTENTS[payload.intentType]["action"])
    assistant_message = _record_smart_deck_message(
        db,
        workspace_id=workspace.id,
        deck_id=deck.id,
        role="assistant",
        content=insight["summary"],
        selected_source_slide_ids=selected_slide_ids,
        metadata_json={
            "assistantRunId": run_id,
            "intentType": payload.intentType,
            "scope": payload.scope,
            "provider": provider,
            "model": resolved_model if provider in {"anthropic", "openai", "openrouter"} else None,
            "credentialSource": claude_config.get("source"),
            "insight": insight,
            "userMessageId": user_message.id,
        },
    )
    artifact_payload = {
        "runId": run_id,
        "intentType": payload.intentType,
        "scope": payload.scope,
        "outputType": ASSISTANT_OUTPUT_TYPES.get(payload.intentType, "insight"),
        "provider": provider,
        "model": resolved_model if provider in {"anthropic", "openai", "openrouter"} else None,
        "credentialSource": claude_config.get("source"),
        "inputContext": context,
        "insight": insight,
        "saveInsight": payload.saveInsight,
        "messageIds": {
            "user": user_message.id,
            "assistant": assistant_message.id,
        },
    }
    artifact_pointer = _write_json_artifact_to_storage(
        db,
        deck.id,
        run_id,
        artifact_payload,
    )
    artifact = _record_llm_artifact(
        db,
        deck_id=deck.id,
        artifact_type=SMART_DECK_ASSISTANT_ARTIFACT_TYPE,
        artifact_key=run_id,
        summary=insight["summary"],
        payload_json=artifact_pointer,
        metrics_json={
            "selectedSlideCount": len(selected_slides),
            "instructionLength": len(payload.instruction),
            "missingEvidenceCount": len(insight["missingEvidence"]),
            "artifactStoragePath": artifact_pointer["storagePath"],
            "artifactStorageProvider": artifact_pointer["storageProvider"],
        },
        store_payload=False,
    )
    db.commit()
    db.refresh(assistant_message)
    db.refresh(artifact)
    return {
        "runId": run_id,
        "deckId": deck.id,
        "intentType": payload.intentType,
        "scope": payload.scope,
        "status": "completed",
        "outputType": ASSISTANT_OUTPUT_TYPES.get(payload.intentType, "insight"),
        "provider": provider,
        "model": resolved_model if provider in {"anthropic", "openai", "openrouter"} else None,
        "inputContext": context,
        "insight": insight,
        "assistantMessage": _map_message(assistant_message),
        "savedArtifactId": artifact.id,
    }


def list_design_tokens(db: Session, deck_id: str) -> dict | None:
    if db.query(Deck.id).filter(Deck.id == deck_id).first() is None:
        return None
    tokens = db.query(DesignToken).filter(DesignToken.deck_id == deck_id).order_by(DesignToken.created_at.desc()).all()
    return {"designTokens": [_map_design_token(token) for token in tokens]}
