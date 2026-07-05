from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.connected_account import ConnectedAccountConnectRequest, ConnectedAccountListRouteResponse
from app.schemas.profile import UserProfileRouteResponse, UserProfileUpdateRequest
from app.services.connected_account_service import connect_account_for_testing, list_connected_accounts
from app.services.profile_service import get_profile_summary, update_profile

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/profile", response_model=UserProfileRouteResponse)
def account_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileRouteResponse:
    return UserProfileRouteResponse(profile=get_profile_summary(db, current_user))


@router.patch("/profile", response_model=UserProfileRouteResponse)
def account_profile_patch(
    payload: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileRouteResponse:
    return UserProfileRouteResponse(profile=update_profile(db, current_user, payload.model_dump(exclude_unset=True)))


@router.get("/connected-accounts", response_model=ConnectedAccountListRouteResponse)
def account_connected_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConnectedAccountListRouteResponse:
    return ConnectedAccountListRouteResponse(accounts=list_connected_accounts(db, current_user))


@router.post("/connected-accounts", response_model=ConnectedAccountListRouteResponse)
def account_connected_accounts_connect(
    payload: ConnectedAccountConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConnectedAccountListRouteResponse:
    if payload.provider not in {"microsoft", "linkedin"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported connected-account provider.",
        )
    connect_account_for_testing(db, current_user, payload.provider, origin=payload.origin)
    return ConnectedAccountListRouteResponse(accounts=list_connected_accounts(db, current_user))
