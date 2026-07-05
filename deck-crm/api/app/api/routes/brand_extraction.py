from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import User
from app.schemas.brand_profile import (
    BrandExtractionStatusResponse,
    ExtractDeckBrandRouteResponse,
    DeckBrandProfileRouteResponse,
    UpdateDeckBrandProfileRequest,
)
from app.services.brand_enrichment_service import enrich_brand_profile_after_extract
from app.services.brand_extraction_service import (
    extract_deck_brand,
    get_deck_brand_asset_file,
    get_deck_brand_profile,
    update_deck_brand_profile,
)
from app.services.brand_status_service import get_deck_brand_status

router = APIRouter(prefix="/products/deck-aistack-codes/decks", tags=["brand-extraction"])


@router.post("/{deck_id}/brand/extract", response_model=ExtractDeckBrandRouteResponse)
async def deck_brand_extract(
    deck_id: str,
    companyUrl: str | None = Form(default=None),
    logoFile: UploadFile | None = File(default=None),
    brandGuidelinesFile: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExtractDeckBrandRouteResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    try:
        profile = await extract_deck_brand(db, deck_id, companyUrl, logoFile, brandGuidelinesFile)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")

    try:
        enrich_brand_profile_after_extract(db, deck_id)
        enriched_profile = get_deck_brand_profile(db, deck_id)
        if enriched_profile is not None:
            profile = enriched_profile
    except Exception:
        db.rollback()

    return ExtractDeckBrandRouteResponse(brandProfileId=profile.id, brandProfile=profile)


@router.get("/{deck_id}/brand/status", response_model=BrandExtractionStatusResponse)
def deck_brand_status(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BrandExtractionStatusResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    status_payload = get_deck_brand_status(db, deck_id)
    if status_payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return status_payload


@router.get("/{deck_id}/brand-assets/{asset_id}")
def deck_brand_asset(
    deck_id: str,
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    asset_file = get_deck_brand_asset_file(db, deck_id, asset_id)
    if asset_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand asset not found")

    path, media_type = asset_file
    return FileResponse(path, media_type=media_type)


@router.get("/{deck_id}/brand-profile", response_model=DeckBrandProfileRouteResponse)
def deck_brand_profile(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeckBrandProfileRouteResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    profile = get_deck_brand_profile(db, deck_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand profile not found")
    return DeckBrandProfileRouteResponse(deckId=deck_id, brandProfile=profile)


@router.patch("/{deck_id}/brand-profile", response_model=DeckBrandProfileRouteResponse)
def deck_brand_profile_patch(
    deck_id: str,
    payload: UpdateDeckBrandProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeckBrandProfileRouteResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    profile = update_deck_brand_profile(db, deck_id, payload.model_dump(exclude_unset=True))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand profile not found")
    return DeckBrandProfileRouteResponse(deckId=deck_id, brandProfile=profile)
