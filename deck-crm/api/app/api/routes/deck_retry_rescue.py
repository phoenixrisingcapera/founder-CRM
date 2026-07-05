from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import User
from app.services.deck_processing_visibility_service import get_deck_processing_visibility
from app.services.deck_workflow_service import queue_source_extraction

logger = logging.getLogger(__name__)
router = APIRouter(tags=["deck-retry-rescue"])


def _safe_processing_visibility(db: Session, deck_id: str) -> dict | None:
    try:
        return get_deck_processing_visibility(db, deck_id)
    except Exception:
        logger.exception("retry_deck_processing_visibility_failed", extra={"deck_id": deck_id})
        return None


@router.post("/products/deck-aistack-codes/decks/{deck_id}/retry")
def retry_deck_processing_rescue(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    deck = get_user_deck_or_404(db, current_user, deck_id)

    try:
        processing = queue_source_extraction(db, deck.id, requested_by_user_id=current_user.id)
        run_id = processing.get("jobId") if isinstance(processing, dict) else None
        run_status = str(processing.get("status") or "") if isinstance(processing, dict) else ""
        visibility = _safe_processing_visibility(db, deck.id)
        return {
            "ok": True,
            "deck_id": deck.id,
            "deckId": deck.id,
            "processing": processing,
            "visibility": visibility,
            "nextAction": (visibility or {}).get("nextAction") or (processing or {}).get("nextAction") or "wait",
        }
    except ValueError as exc:
        db.rollback()
        visibility = _safe_processing_visibility(db, deck.id)
        message = str(exc) or "Deck processing could not be queued."
        logger.warning("retry_deck_processing_rescue_rejected", extra={"deck_id": deck.id, "reason": message})
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": message,
                "deckId": deck.id,
                "visibility": visibility,
                "retryable": "source file" not in message.lower(),
            },
        ) from exc
    except Exception as exc:
        db.rollback()
        visibility = _safe_processing_visibility(db, deck.id)
        logger.exception("retry_deck_processing_rescue_failed", extra={"deck_id": deck.id})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Could not queue Smart Deck processing. The source deck is saved, but processing could not start.",
                "deckId": deck.id,
                "visibility": visibility,
                "retryable": True,
            },
        ) from exc
