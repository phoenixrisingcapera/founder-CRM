from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import User
from app.services.product_analytics_service import record_deck_product_event

router = APIRouter(prefix="/decks", tags=["product-analytics"])


class DeckProductEventCreate(BaseModel):
    model_config = ConfigDict(extra="allow")

    eventName: str = Field(min_length=1, max_length=120)
    surface: str = Field(default="unknown", max_length=80)
    entityType: str | None = Field(default=None, max_length=80)
    entityId: str | None = Field(default=None, max_length=128)
    sessionId: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] | None = None


@router.post("/{deck_id}/analytics/events")
def deck_product_event(
    deck_id: str,
    payload: DeckProductEventCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    deck = get_user_deck_or_404(db, current_user, deck_id)
    event = record_deck_product_event(
        db,
        event_name=payload.eventName,
        actor=current_user,
        deck=deck,
        request=request,
        surface=payload.surface,
        entity_type=payload.entityType,
        entity_id=payload.entityId,
        session_id=payload.sessionId,
        metadata=payload.metadata,
        commit=True,
    )
    return {"event": event, "recorded": event is not None}
