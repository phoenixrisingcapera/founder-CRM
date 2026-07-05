from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import User
from app.schemas.analysis import AnalysisFindingsRouteResponse
from app.services.analysis_service import analyse_deck, get_findings

router = APIRouter(prefix="/decks", tags=["analysis"])


@router.post("/{deck_id}/analyse")
def analyse(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    result = analyse_deck(db, deck_id)
    if not result:
        raise HTTPException(status_code=404, detail="Deck not found")
    return result


@router.get("/{deck_id}/findings", response_model=AnalysisFindingsRouteResponse)
def findings(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisFindingsRouteResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    return AnalysisFindingsRouteResponse(findings=get_findings(db, deck_id))
