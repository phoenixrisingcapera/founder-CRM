from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import User
from app.services.deck_artifact_listing_service import list_deck_llm_artifacts

router = APIRouter(tags=["deck-artifacts"])


def _deck_artifacts_response(
    *,
    deck_id: str,
    request: Request,
    artifact_type: str | None = None,
    limit: int = 100,
    current_user: User,
    db: Session,
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    try:
        return list_deck_llm_artifacts(
            db,
            deck_id,
            artifact_type=artifact_type,
            limit=limit,
        )
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Deck LLM artifacts are temporarily unavailable.",
                "failureCategory": "deck_llm_artifacts_load",
                "requestId": getattr(request.state, "request_id", None),
            },
        ) from exc


def product_deck_artifacts(
    deck_id: str,
    request: Request,
    artifact_type: str | None = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return _deck_artifacts_response(
        deck_id=deck_id,
        artifact_type=artifact_type,
        limit=limit,
        request=request,
        current_user=current_user,
        db=db,
    )


@router.get("/decks/{deck_id}/artifacts")
def deck_artifacts(
    deck_id: str,
    request: Request,
    artifact_type: str | None = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return _deck_artifacts_response(
        deck_id=deck_id,
        artifact_type=artifact_type,
        limit=limit,
        request=request,
        current_user=current_user,
        db=db,
    )
