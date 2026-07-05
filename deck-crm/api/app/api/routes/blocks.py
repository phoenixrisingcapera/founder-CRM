from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import User
from app.schemas.block import SlideBlockPatch
from app.services.block_service import get_blocks, patch_block

router = APIRouter(prefix="/decks", tags=["blocks"])


@router.get("/{deck_id}/slides/{slide_id}/blocks")
def blocks(
    deck_id: str,
    slide_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[dict]]:
    get_user_deck_or_404(db, current_user, deck_id)
    return {"blocks": get_blocks(db, deck_id, slide_id)}


@router.patch("/{deck_id}/blocks/{block_id}")
def block_patch(
    deck_id: str,
    block_id: str,
    payload: SlideBlockPatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    block = patch_block(db, deck_id, block_id, payload.text)
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    return {"block": block}
