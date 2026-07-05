from __future__ import annotations

from sqlalchemy.orm import Session, selectinload

from app.agents.adaptation_suggestion_agent import run as adaptation_suggestion_run
from app.agents.audience_alignment_agent import run as audience_alignment_run
from app.agents.block_classifier_agent import run as block_classifier_run
from app.agents.diligence_gap_agent import run as diligence_gap_run
from app.core.security import generate_id
from app.db.models import (
    AdaptationSuggestion,
    AnalysisFinding,
    AnalysisRun,
    Deck,
    DeckExport,
    DeckFile,
    DeckLlmArtifact,
    DeckSlide,
    DeckSlideBlock,
    DeckSlideRevision,
    SmartEditSuggestion,
    User,
    Workspace,
)
from app.services.deck_state_machine_service import DeckState, canonical_deck_state
from app.services.save_confirmation_service import record_save_confirmation
from app.services.smart_deck_llm_service import _resolve_claude_config
from app.services.bucket_artifact_service import get_bucket_artifact_service
from app.services.upload_storage import get_upload_storage
from app.services.user_service import ensure_workspace
from app.services.workspace_summary_service import resolve_workspace_for_user


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def _deck_state(deck: Deck) -> str:
    return canonical_deck_state(deck.status).value


def _map_deck(deck: Deck) -> dict:
    state = _deck_state(deck)
    return {
        "id": deck.id,
        "workspace_id": deck.workspace_id,
        "title": deck.title,
        "audience": deck.audience,
        "purpose": deck.purpose,
        "status": state,
        "state": state,
        "deckStatus": state,
        "summary": deck.summary,
        "created_at": deck.created_at,
        "updated_at": deck.updated_at,
    }


def _map_file(file: DeckFile | None) -> dict | None:
    if file is None:
        return None
    return {
        "id": file.id,
        "deck_id": file.deck_id,
        "filename": file.original_filename or file.filename,
        "stored_filename": file.filename,
        "mime_type": file.mime_type,
        "size": file.size,
        "storage_path": file.storage_path,
        "uploaded_at": _iso(file.uploaded_at),
    }


def _signed_upload_url(storage_path: str | None) -> str | None:
    if not storage_path:
        return None
    try:
        return get_upload_storage().create_signed_get_url(storage_path)
    except Exception:
        return None


def _signed_artifact_url(storage_path: str | None) -> str | None:
    if not storage_path:
        return None
    try:
        return get_bucket_artifact_service().create_signed_url_sync(key=storage_path)
    except Exception:
        return None


def _map_slide(slide: DeckSlide) -> dict:
    preview_asset = next(
        (
            asset
            for asset in sorted(slide.assets, key=lambda item: item.created_at, reverse=True)
            if asset.asset_type == "source_preview" and asset.storage_path
        ),
        None,
    )
    preview_url = f"/api/decks/{slide.deck_id}/slides/{slide.id}/preview" if preview_asset else None
    signed_preview_url = _signed_upload_url(preview_asset.storage_path) if preview_asset else None
    resolved_preview_url = signed_preview_url or preview_url
    return {
        "id": slide.id,
        "deck_id": slide.deck_id,
        "deckId": slide.deck_id,
        "slide_index": slide.slide_index,
        "slideIndex": slide.slide_index,
        "slide_number": slide.slide_number or slide.source_page_number or slide.slide_index,
        "slideNumber": slide.slide_number or slide.source_page_number or slide.slide_index,
        "title": slide.title,
        "role": slide.role,
        "raw_text": slide.raw_text,
        "rawText": slide.raw_text,
        "extractedText": slide.raw_text,
        "narrative_notes": slide.narrative_notes,
        "narrativeNotes": slide.narrative_notes,
        "status": "ready" if preview_asset else "pending",
        "previewUrl": resolved_preview_url,
        "preview_url": resolved_preview_url,
        "previewImageUrl": resolved_preview_url,
        "thumbnailUrl": resolved_preview_url,
        "signedPreviewUrl": signed_preview_url,
        "signedThumbnailUrl": signed_preview_url,
        "previewProxyUrl": preview_url,
        "previewWidth": preview_asset.width if preview_asset else None,
        "previewHeight": preview_asset.height if preview_asset else None,
        "previewMimeType": preview_asset.mime_type if preview_asset else slide.thumbnail_mime_type,
    }


def _map_llm_artifact(artifact: DeckLlmArtifact) -> dict:
    storage_path = artifact.bucket_payload_key
    if not storage_path and isinstance(artifact.payload_json, dict):
        storage_path = artifact.payload_json.get("storagePath")
    return {
        "id": artifact.id,
        "deckId": artifact.deck_id,
        "artifactType": artifact.artifact_type,
        "artifactKey": artifact.artifact_key,
        "schemaVersion": artifact.schema_version,
        "status": artifact.status,
        "summary": artifact.summary,
        "bucketPayloadKey": storage_path,
        "signedUrl": _signed_artifact_url(storage_path),
        "metricsJson": artifact.metrics_json,
        "createdAt": _iso(artifact.created_at),
        "updatedAt": _iso(artifact.updated_at),
    }


def _map_block(block: DeckSlideBlock) -> dict:
    return {
        "id": block.id,
        "slide_id": block.slide_id,
        "block_index": block.block_index,
        "raw_text": block.raw_text,
        "normalized_text": block.normalized_text,
        "block_type": block.block_type,
        "position": block.position,
        "style": block.style,
    }


def _deck_agent_context(deck: Deck) -> dict:
    slides = sorted(deck.slides, key=lambda item: item.slide_index)
    return {
        "deck": {
            "id": deck.id,
            "title": deck.title,
            "audience": deck.audience,
            "purpose": deck.purpose,
            "summary": deck.summary,
            "status": _deck_state(deck),
        },
        "slides": [
            {
                "id": slide.id,
                "slide_index": slide.slide_index,
                "slide_number": slide.slide_number or slide.source_page_number or slide.slide_index + 1,
                "title": slide.title,
                "role": slide.role,
                "semantic_slide_type": slide.semantic_slide_type,
                "summary": slide.summary,
                "raw_text": slide.raw_text,
                "blocks": [
                    {
                        "id": block.id,
                        "block_index": block.block_index,
                        "block_type": block.block_type,
                        "raw_text": block.raw_text,
                        "normalized_text": block.normalized_text,
                    }
                    for block in sorted(slide.blocks, key=lambda item: item.block_index)[:12]
                ],
            }
            for slide in slides[:20]
        ],
    }


def _map_finding(finding: AnalysisFinding) -> dict:
    return {
        "id": finding.id,
        "deck_id": finding.deck_id,
        "slide_id": finding.slide_id,
        "block_id": finding.block_id,
        "title": finding.title,
        "detail": finding.detail,
        "severity": finding.severity,
        "category": finding.category,
    }


def _map_adaptation_suggestion(suggestion: AdaptationSuggestion) -> dict:
    return {
        "id": suggestion.id,
        "deck_id": suggestion.deck_id,
        "slide_id": suggestion.slide_id,
        "block_id": suggestion.block_id,
        "title": suggestion.title,
        "reason": suggestion.reason,
        "suggested_text": suggestion.suggested_text,
        "status": suggestion.status,
        "audience": suggestion.audience,
    }


def _map_smart_edit_suggestion(suggestion: SmartEditSuggestion) -> dict:
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


def _map_revision(revision: DeckSlideRevision) -> dict:
    return {
        "id": revision.id,
        "deck_id": revision.deck_id,
        "slide_id": revision.slide_id,
        "block_id": revision.block_id,
        "previous_text": revision.previous_text,
        "next_text": revision.next_text,
        "reason": revision.reason,
        "created_at": _iso(revision.created_at),
    }


def _resolve_workspace(db: Session, workspace_id: str) -> Workspace | None:
    return db.query(Workspace).filter(Workspace.id == workspace_id).one_or_none()


def list_decks(db: Session, user_id: str | None = None, include_all: bool = False) -> list[dict]:
    query = db.query(Deck)
    if user_id is not None and not include_all:
        query = query.join(Workspace, Workspace.id == Deck.workspace_id).filter(
            (Deck.user_id == user_id) | (Workspace.user_id == user_id)
        )
    return [_map_deck(deck) for deck in query.order_by(Deck.updated_at.desc(), Deck.created_at.desc()).all()]


def create_deck(db: Session, payload: dict, user_id: str | None = None) -> dict | None:
    requested_workspace_id = payload.get("workspace_id")
    workspace = _resolve_workspace(db, requested_workspace_id) if isinstance(requested_workspace_id, str) else None

    if workspace is None and user_id is not None:
        placeholder_workspace_ids = {"ws_01", "ws_demo", "ws_default"}
        if requested_workspace_id is None or requested_workspace_id in placeholder_workspace_ids:
            workspace = resolve_workspace_for_user(db, user_id)
        if workspace is None:
            user = db.query(User).filter(User.id == user_id).one_or_none()
            if user is not None:
                workspace = ensure_workspace(db, user)

    if workspace is None:
        return None
    if user_id is not None and workspace.user_id != user_id:
        return None

    deck = Deck(
        id=generate_id("deck"),
        workspace_id=workspace.id,
        user_id=user_id,
        title=payload["title"],
        audience=payload["audience"],
        purpose=payload["purpose"],
        status=DeckState.PENDING.value,
        summary="Deck record created. Upload is pending.",
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return _map_deck(deck)


def get_deck(db: Session, deck_id: str) -> dict | None:
    deck = (
        db.query(Deck)
        .options(
            selectinload(Deck.file),
            selectinload(Deck.slides).selectinload(DeckSlide.blocks),
            selectinload(Deck.slides).selectinload(DeckSlide.assets),
            selectinload(Deck.llm_artifacts),
        )
        .filter(Deck.id == deck_id)
        .one_or_none()
    )
    if deck is None:
        return None

    return {
        "deck": _map_deck(deck),
        "file": _map_file(deck.file),
        "slides": [_map_slide(slide) for slide in sorted(deck.slides, key=lambda item: item.slide_index)],
        "llm_artifacts": [
            _map_llm_artifact(artifact)
            for artifact in sorted(deck.llm_artifacts, key=lambda item: item.created_at, reverse=True)
        ],
        "llmArtifacts": [
            _map_llm_artifact(artifact)
            for artifact in sorted(deck.llm_artifacts, key=lambda item: item.created_at, reverse=True)
        ],
        "findings": get_findings(db, deck.id),
        "suggestions": get_suggestions(db, deck.id),
        "smart_edit_suggestions": [
            _map_smart_edit_suggestion(item)
            for item in db.query(SmartEditSuggestion)
            .filter(SmartEditSuggestion.deck_id == deck.id)
            .order_by(SmartEditSuggestion.id.asc())
            .all()
        ],
        "revisions": [
            _map_revision(item)
            for item in db.query(DeckSlideRevision)
            .filter(DeckSlideRevision.deck_id == deck.id)
            .order_by(DeckSlideRevision.created_at.desc())
            .all()
        ],
    }


def get_status(db: Session, deck_id: str) -> dict | None:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        return None
    from app.services.deck_workflow_service import get_deck_workflow_state

    workflow = get_deck_workflow_state(db, deck_id)
    if workflow is None:
        state = _deck_state(deck)
        return {"status": state, "state": state, "deckStatus": state, "updated_at": deck.updated_at}

    workflow_status = str(workflow.get("status") or _deck_state(deck))
    return {
        "status": workflow_status,
        "state": workflow_status,
        "deckStatus": workflow_status,
        "phase": workflow.get("phase"),
        "nextAction": workflow.get("nextAction"),
        "blockingReason": workflow.get("blockingReason"),
        "workflowId": workflow.get("workflowId"),
        "updated_at": workflow.get("updatedAt") or deck.updated_at,
        "activeJob": workflow.get("activeJob"),
    }


def get_slides(db: Session, deck_id: str) -> list[dict]:
    return [
        _map_slide(slide)
        for slide in db.query(DeckSlide)
        .filter(DeckSlide.deck_id == deck_id)
        .options(selectinload(DeckSlide.assets))
        .order_by(DeckSlide.slide_index.asc())
        .all()
    ]


def get_blocks(db: Session, deck_id: str, slide_id: str) -> list[dict]:
    return [
        _map_block(block)
        for block in db.query(DeckSlideBlock)
        .join(DeckSlide, DeckSlide.id == DeckSlideBlock.slide_id)
        .filter(DeckSlide.deck_id == deck_id, DeckSlide.id == slide_id)
        .order_by(DeckSlideBlock.block_index.asc())
        .all()
    ]


def patch_block(db: Session, deck_id: str, block_id: str, text: str, reason: str = "Manual block edit") -> dict | None:
    block = (
        db.query(DeckSlideBlock)
        .join(DeckSlide, DeckSlide.id == DeckSlideBlock.slide_id)
        .filter(DeckSlide.deck_id == deck_id, DeckSlideBlock.id == block_id)
        .one_or_none()
    )
    if block is None:
        return None

    previous = block.raw_text
    block.raw_text = text
    block.normalized_text = text.strip()
    db.add(
        DeckSlideRevision(
            id=generate_id("rev"),
            deck_id=deck_id,
            slide_id=block.slide_id,
            block_id=block.id,
            previous_text=previous,
            next_text=text,
            reason=reason,
        )
    )
    db.commit()
    db.refresh(block)
    return _map_block(block)


def get_findings(db: Session, deck_id: str) -> list[dict]:
    return [
        _map_finding(finding)
        for finding in db.query(AnalysisFinding)
        .filter(AnalysisFinding.deck_id == deck_id)
        .order_by(AnalysisFinding.severity.desc(), AnalysisFinding.title.asc())
        .all()
    ]


def get_suggestions(db: Session, deck_id: str) -> list[dict]:
    return [
        _map_adaptation_suggestion(suggestion)
        for suggestion in db.query(AdaptationSuggestion)
        .filter(AdaptationSuggestion.deck_id == deck_id)
        .order_by(AdaptationSuggestion.title.asc())
        .all()
    ]


def patch_suggestion(db: Session, deck_id: str, suggestion_id: str, status: str, edited_text: str | None = None) -> dict | None:
    return patch_suggestion_with_audit(
        db,
        deck_id,
        suggestion_id,
        status,
        edited_text,
        audit_metadata=None,
    )


def patch_suggestion_with_audit(
    db: Session,
    deck_id: str,
    suggestion_id: str,
    status: str,
    edited_text: str | None = None,
    audit_metadata: dict | None = None,
) -> dict | None:
    suggestion = (
        db.query(AdaptationSuggestion)
        .filter(AdaptationSuggestion.deck_id == deck_id, AdaptationSuggestion.id == suggestion_id)
        .one_or_none()
    )
    if suggestion is not None:
        suggestion.status = status
        if edited_text:
            suggestion.suggested_text = edited_text
        _record_suggestion_audit(
            db,
            deck_id=deck_id,
            suggestion_id=suggestion.id,
            suggestion_kind="adaptation",
            decision=status,
            applied=False,
            audit_metadata=audit_metadata,
        )
        db.commit()
        db.refresh(suggestion)
        return _map_adaptation_suggestion(suggestion)

    smart_suggestion = (
        db.query(SmartEditSuggestion)
        .filter(SmartEditSuggestion.deck_id == deck_id, SmartEditSuggestion.id == suggestion_id)
        .one_or_none()
    )
    if smart_suggestion is None:
        return None

    smart_suggestion.status = status
    if edited_text:
        smart_suggestion.suggested_text = edited_text
    applied = False
    if status in {"accepted", "applied", "edited"}:
        patch_block(
            db,
            deck_id,
            smart_suggestion.block_id,
            smart_suggestion.suggested_text,
            reason="Smart Edit accepted" if status == "accepted" else "Smart Edit edited",
        )
        smart_suggestion.status = "applied" if status == "accepted" else status
        applied = True
    _record_suggestion_audit(
        db,
        deck_id=deck_id,
        suggestion_id=smart_suggestion.id,
        suggestion_kind="smart_edit",
        decision=status,
        applied=applied,
        audit_metadata=audit_metadata,
    )
    db.commit()
    db.refresh(smart_suggestion)
    return _map_smart_edit_suggestion(smart_suggestion)


def _record_suggestion_audit(
    db: Session,
    *,
    deck_id: str,
    suggestion_id: str,
    suggestion_kind: str,
    decision: str,
    applied: bool,
    audit_metadata: dict | None,
) -> None:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    metadata = {
        "suggestionKind": suggestion_kind,
        "decision": decision,
        "applied": applied,
        **(audit_metadata or {}),
    }
    record_save_confirmation(
        db,
        deck_id=deck_id,
        workspace_id=deck.workspace_id if deck is not None else None,
        user_id=(audit_metadata or {}).get("userId") if audit_metadata else None,
        event_type=f"smart_edit_{decision}",
        entity_type="smart_edit_suggestion",
        entity_id=suggestion_id,
        title="Smart Edit decision saved",
        message=f"Smart Edit suggestion marked {decision}.",
        source_surface="due_diligence_smart_edit",
        source_route=f"/decks/{deck_id}/due-diligence",
        dedupe_key=f"smart_edit:{deck_id}:{suggestion_id}:{decision}:{len(str(metadata))}",
        metadata=metadata,
    )


def analyse_deck(db: Session, deck_id: str) -> dict | None:
    deck = (
        db.query(Deck)
        .options(selectinload(Deck.slides).selectinload(DeckSlide.blocks))
        .filter(Deck.id == deck_id)
        .one_or_none()
    )
    if deck is None:
        return None

    slides = sorted(deck.slides, key=lambda item: item.slide_index)
    first_slide = slides[0] if slides else None
    first_block = sorted(first_slide.blocks, key=lambda item: item.block_index)[0] if first_slide and first_slide.blocks else None

    db.query(AnalysisFinding).filter(AnalysisFinding.deck_id == deck.id).delete(synchronize_session=False)
    db.query(AdaptationSuggestion).filter(AdaptationSuggestion.deck_id == deck.id).delete(synchronize_session=False)

    block_classifier_run(deck.id)
    audience_alignment_run(deck.audience, deck.purpose)
    deck_context = _deck_agent_context(deck)
    provider_config = _resolve_claude_config(db, deck, use_case="analysis")
    slide_ids = {slide.id for slide in slides}
    block_ids = {block.id for slide in slides for block in slide.blocks}

    if first_slide is not None:
        for payload in diligence_gap_run(deck.id, deck_context=deck_context, provider_config=provider_config):
            payload_slide_id = payload.get("slide_id") if payload.get("slide_id") in slide_ids else first_slide.id
            payload_block_id = payload.get("block_id") if payload.get("block_id") in block_ids else (first_block.id if first_block is not None else None)
            db.add(
                AnalysisFinding(
                    id=generate_id("finding"),
                    deck_id=deck.id,
                    slide_id=payload_slide_id,
                    block_id=payload_block_id,
                    title=payload["title"],
                    detail=payload["detail"],
                    severity=payload["severity"],
                    category=payload["category"],
                )
            )
        for payload in adaptation_suggestion_run(deck.id, deck.audience, deck_context=deck_context, provider_config=provider_config):
            payload_slide_id = payload.get("slide_id") if payload.get("slide_id") in slide_ids else first_slide.id
            payload_block_id = payload.get("block_id") if payload.get("block_id") in block_ids else (first_block.id if first_block is not None else None)
            db.add(
                AdaptationSuggestion(
                    id=generate_id("adpt"),
                    deck_id=deck.id,
                    slide_id=payload_slide_id,
                    block_id=payload_block_id,
                    title=payload["title"],
                    reason=payload["reason"],
                    suggested_text=payload["suggested_text"],
                    status="pending",
                    audience=deck.audience,
                )
            )

    db.add(AnalysisRun(id=generate_id("analysis"), deck_id=deck.id, status="completed"))
    db.commit()
    return get_deck(db, deck.id)
