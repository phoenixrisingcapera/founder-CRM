from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import Deck, DesignVersion, GeneratedSlide, SmartDeckWorkspace, User
from app.services.deck_processing_visibility_service import get_deck_processing_visibility
from app.services.workspace_summary_service import soft_delete_workspace_deck

router = APIRouter(prefix="/products/deck-aistack-codes", tags=["product-runtime-hardening"])
logger = logging.getLogger(__name__)


def _diligence_placeholder(deck_id: str, audience: str | None = None) -> dict:
    selected_audience = audience or "Investment Committee"
    return {
        "ok": True,
        "deck_id": deck_id,
        "status": "not_ready",
        "selected_audience": selected_audience,
        "message": "Due diligence workspace is registered but not fully generated for this deck yet.",
        "summary": {
            "title": "Due diligence workspace pending",
            "audience": selected_audience,
            "confidence": "pending",
        },
        "checklist": [
            {
                "key": "market_claims",
                "label": "Market claims",
                "status": "pending",
                "message": "Market claims will be checked when diligence generation runs.",
            },
            {
                "key": "competitor_claims",
                "label": "Competitor claims",
                "status": "pending",
                "message": "Competitor claims will be checked when diligence generation runs.",
            },
            {
                "key": "evidence_gaps",
                "label": "Evidence gaps",
                "status": "pending",
                "message": "Evidence gaps will be surfaced from the saved source deck.",
            },
        ],
        "findings": [],
        "next_action": "run_due_diligence",
    }


def _active_design_version_id_query(db: Session, deck: Deck):
    """Return a query that selects only stable columns used by processing debug.

    The processing page should not fail or log noisy stack traces if a newly-added
    optional column is missing from a lagging production schema. Selecting only the
    design version id keeps this endpoint independent from optional ORM fields such
    as bucket_manifest_key.
    """

    return db.query(DesignVersion.id).filter(
        DesignVersion.deck_id == deck.id,
        DesignVersion.status != "discarded",
    )


def _first_design_version_id(query) -> str | None:
    row = query.first()
    if row is None:
        return None
    value = row[0]
    return str(value) if value else None


def _resolve_active_design_version_id(db: Session, deck: Deck, workspace: SmartDeckWorkspace | None) -> str | None:
    query = _active_design_version_id_query(db, deck)
    candidate_ids = [
        workspace.active_design_version_id if workspace else None,
        deck.current_design_version_id,
    ]
    for candidate_id in candidate_ids:
        if not candidate_id:
            continue
        version_id = _first_design_version_id(query.filter(DesignVersion.id == candidate_id))
        if version_id is not None:
            return version_id

    active_id = _first_design_version_id(
        query.filter(DesignVersion.is_active.is_(True)).order_by(DesignVersion.created_at.desc())
    )
    if active_id is not None:
        return active_id
    return _first_design_version_id(query.order_by(DesignVersion.created_at.desc()))


def _smart_deck_debug_payload(db: Session, deck: Deck) -> dict:
    workspace = db.query(SmartDeckWorkspace).filter(SmartDeckWorkspace.deck_id == deck.id).one_or_none()
    active_design_version_id = _resolve_active_design_version_id(db, deck, workspace)
    generated_slides = []
    if active_design_version_id is not None:
        generated_slides = (
            db.query(GeneratedSlide)
            .filter(
                GeneratedSlide.deck_id == deck.id,
                GeneratedSlide.design_version_id == active_design_version_id,
            )
            .order_by(GeneratedSlide.slide_number.asc())
            .all()
        )

    active_generated_slide_id = workspace.active_generated_slide_id if workspace else None
    active_generated_slide = None
    if active_generated_slide_id:
        active_generated_slide = next((slide for slide in generated_slides if slide.id == active_generated_slide_id), None)
    if active_generated_slide is None and generated_slides:
        active_generated_slide = generated_slides[0]
        active_generated_slide_id = active_generated_slide.id

    render_schema = active_generated_slide.render_schema_json if active_generated_slide is not None else None
    render_elements = render_schema.get("elements") if isinstance(render_schema, dict) else None
    render_schema_element_count = len(render_elements) if isinstance(render_elements, list) else 0
    generated_slide_count = len(generated_slides)
    has_renderable_schema = generated_slide_count > 0 and render_schema_element_count > 0

    return {
        "workspaceId": workspace.id if workspace else None,
        "workspaceStatus": workspace.status if workspace else None,
        "currentDesignVersionId": deck.current_design_version_id,
        "activeDesignVersionId": active_design_version_id,
        "activeGeneratedSlideId": active_generated_slide_id,
        "generatedSlideCount": generated_slide_count,
        "renderSchemaElementCount": render_schema_element_count,
        "hasRenderableSchema": has_renderable_schema,
        "canOpenSmartDeck": has_renderable_schema,
    }


def _with_smart_deck_debug(visibility: dict, smart_deck: dict) -> dict:
    next_action = visibility.get("nextAction") or visibility.get("next_action")
    can_open_from_processing = next_action == "open_smart_deck" or bool(visibility.get("canOpenSmartDeck"))
    has_renderable_schema = bool(smart_deck.get("hasRenderableSchema"))

    if has_renderable_schema and not can_open_from_processing:
        visibility = {
            **visibility,
            "status": "ready",
            "state": "ready",
            "deckExtractionStatus": "ready",
            "nextAction": "open_smart_deck",
            "message": "Smart Deck visualizer has a persisted generated render schema and can open safely.",
            "canOpenSmartDeck": True,
        }

    return {
        **visibility,
        "smartDeck": {
            **smart_deck,
            "processingNextAction": visibility.get("nextAction") or visibility.get("next_action"),
            "processingCanOpenSmartDeck": bool(visibility.get("canOpenSmartDeck")),
        },
    }


def _safe_debug_payload(visibility: dict) -> dict:
    return {
        "workspaceId": None,
        "workspaceStatus": visibility.get("deckStatus"),
        "currentDesignVersionId": None,
        "activeDesignVersionId": None,
        "activeGeneratedSlideId": None,
        "generatedSlideCount": 0,
        "renderSchemaElementCount": 0,
        "hasRenderableSchema": False,
        "canOpenSmartDeck": bool(visibility.get("canOpenSmartDeck")),
    }


@router.get("/decks/{deck_id}/due-diligence")
def due_diligence_workspace(
    deck_id: str,
    audience: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    return _diligence_placeholder(deck_id, audience)


@router.post("/decks/{deck_id}/due-diligence/run")
def run_due_diligence(
    deck_id: str,
    payload: dict | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    audience = str((payload or {}).get("audience") or "Investment Committee")
    return {
        **_diligence_placeholder(deck_id, audience),
        "status": "accepted",
        "message": "Due diligence run accepted. Full generation will be handled by the product worker in a later stage.",
        "next_action": "wait_for_due_diligence",
    }


@router.get("/decks/{deck_id}/processing")
def deck_processing_visibility_with_smart_deck_debug(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    deck = get_user_deck_or_404(db, current_user, deck_id)
    visibility = get_deck_processing_visibility(db, deck_id)
    if visibility is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    try:
        smart_deck = _smart_deck_debug_payload(db, deck)
    except Exception:
        logger.exception("product_runtime_hardening_processing_debug_failed", extra={"deck_id": deck_id})
        smart_deck = _safe_debug_payload(visibility)
    return _with_smart_deck_debug(visibility, smart_deck)


@router.post("/decks/{deck_id}/soft-delete")
def soft_delete_deck_idempotent(
    deck_id: str,
    workspace_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    # Access check still happens before idempotent handling. If the deck truly
    # does not belong to this user, the shared access guard raises 404.
    get_user_deck_or_404(db, current_user, deck_id)
    try:
        return soft_delete_workspace_deck(db, deck_id, workspace_id)
    except ValueError:
        return {
            "ok": True,
            "deck_id": deck_id,
            "soft_deleted": True,
            "noop": True,
            "message": "Deck was already removed or is no longer visible in this workspace.",
        }
