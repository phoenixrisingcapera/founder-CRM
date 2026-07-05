from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import DeckSlide, DeckSlideAsset, User
from app.services.deck_file_service import get_upload_root, resolve_upload_path
from app.services.slide_service import get_slides

router = APIRouter(prefix="/decks", tags=["slides"])


@router.get("/{deck_id}/slides")
def slides(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[dict]]:
    get_user_deck_or_404(db, current_user, deck_id)
    return {"slides": get_slides(db, deck_id)}


@router.get("/{deck_id}/slides/{slide_id}/preview")
def slide_preview(
    deck_id: str,
    slide_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    asset = (
        db.query(DeckSlideAsset)
        .join(DeckSlide, DeckSlide.id == DeckSlideAsset.slide_id)
        .filter(
            DeckSlide.deck_id == deck_id,
            DeckSlide.id == slide_id,
            DeckSlideAsset.asset_type == "source_preview",
        )
        .order_by(DeckSlideAsset.created_at.desc())
        .first()
    )
    if asset is None or not asset.storage_path:
        raise HTTPException(status_code=404, detail="Slide preview not found")

    root = get_upload_root().resolve()
    preview_path = resolve_upload_path(asset.storage_path)
    if preview_path is None:
        raise HTTPException(status_code=404, detail="Slide preview not found")
    if not _is_relative_to(preview_path, root) or not preview_path.is_file():
        raise HTTPException(status_code=404, detail="Slide preview not found")

    return FileResponse(preview_path, media_type=asset.mime_type or "image/png")


@router.get("/{deck_id}/slides/{slide_id}/assets/{asset_id}")
def slide_asset(
    deck_id: str,
    slide_id: str,
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    asset = (
        db.query(DeckSlideAsset)
        .join(DeckSlide, DeckSlide.id == DeckSlideAsset.slide_id)
        .filter(
            DeckSlide.deck_id == deck_id,
            DeckSlide.id == slide_id,
            DeckSlideAsset.id == asset_id,
        )
        .first()
    )
    if asset is None or not asset.storage_path:
        raise HTTPException(status_code=404, detail="Slide asset not found")

    asset_path = resolve_upload_path(asset.storage_path)
    if asset_path is None or not asset_path.is_file():
        raise HTTPException(status_code=404, detail="Slide asset not found")

    return FileResponse(asset_path, media_type=asset.mime_type or "application/octet-stream")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
