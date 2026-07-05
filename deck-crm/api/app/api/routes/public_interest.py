from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.public_interest import InterestLeadCreate, PublicInterestResponse
from app.services.public_interest_service import create_interest_lead
from app.services.rate_limit_service import enforce_rate_limit
from app.services.turnstile_service import verify_turnstile_token

router = APIRouter(prefix="/public", tags=["public"])


def _public_interest_turnstile_required() -> bool:
    value = os.getenv("PUBLIC_INTEREST_TURNSTILE_REQUIRED", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


@router.post("/interest", response_model=PublicInterestResponse, status_code=status.HTTP_201_CREATED)
def create_public_interest(
    payload: InterestLeadCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str | bool]:
    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = forwarded_for.split(",", 1)[0].strip() if forwarded_for else request.client.host if request.client else "unknown"
    enforce_rate_limit(f"public-interest:ip:{client_ip}", db=db, limit=20, window_seconds=3600)
    enforce_rate_limit(f"public-interest:email:{payload.email.lower()}", db=db, limit=3, window_seconds=86400)
    if payload.turnstileToken or _public_interest_turnstile_required():
        verify_turnstile_token(payload.turnstileToken, remote_ip=client_ip)
    lead = create_interest_lead(db, payload)
    return {
        "ok": True,
        "lead_id": lead.id,
        "message": "Thanks — we’ve recorded your interest in Deck AI Stack.",
    }
