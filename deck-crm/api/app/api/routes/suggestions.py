from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import User
from app.schemas.analysis import AdaptationSuggestionsRouteResponse
from app.schemas.suggestion import SuggestionPatch
from app.services.adaptation_service import get_suggestions, patch_suggestion

router = APIRouter(prefix="/decks", tags=["suggestions"])


@router.get("/{deck_id}/suggestions", response_model=AdaptationSuggestionsRouteResponse)
def suggestions(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdaptationSuggestionsRouteResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    return AdaptationSuggestionsRouteResponse(suggestions=get_suggestions(db, deck_id))


@router.patch("/{deck_id}/suggestions/{suggestion_id}")
def suggestion_patch(
    deck_id: str,
    suggestion_id: str,
    payload: SuggestionPatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    suggestion = patch_suggestion(db, deck_id, suggestion_id, payload.status, payload.edited_text)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return {"suggestion": suggestion}
