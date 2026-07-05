from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.db.models import User
from app.schemas.user import AuthSessionResponse, UserCreate, UserSignIn, UserSummary
from app.services.auth_session_service import revoke_auth_session
from app.services.user_service import authenticate_user, build_auth_response, create_user, serialize_user
from app.services.rate_limit_service import enforce_rate_limit
from app.services.security_audit_service import record_security_event

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _sign_up_user(payload: UserCreate, request: Request, db: Session) -> dict:
    enforce_rate_limit(f"auth:signup:ip:{_client_ip(request)}", db=db, limit=10, window_seconds=3600)
    enforce_rate_limit(f"auth:signup:email:{payload.email.lower()}", db=db, limit=3, window_seconds=3600)
    if not payload.accepted_terms:
        record_security_event(
            db,
            action="auth.sign_up",
            result="denied",
            actor_email=payload.email,
            resource_type="user",
            request=request,
            details={"reason": "terms_not_accepted"},
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You must accept the terms to create an account")

    if not settings.public_signup_enabled:
        record_security_event(
            db,
            action="auth.sign_up",
            result="denied",
            actor_email=payload.email,
            resource_type="user",
            request=request,
            details={"reason": "public_signup_disabled"},
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Public sign-up is disabled")

    public_payload = payload.model_copy(update={"role": "general"})
    try:
        user = create_user(db, public_payload)
    except ValueError as exc:
        record_security_event(
            db,
            action="auth.sign_up",
            result="failure",
            actor_email=payload.email,
            resource_type="user",
            request=request,
            details={"reason": str(exc)},
            commit=True,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_security_event(
        db,
        action="auth.sign_up",
        result="success",
        actor=user,
        resource_type="user",
        resource_id=user.id,
        request=request,
        commit=True,
    )
    return build_auth_response(db, user)


@router.post("/sign-up", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def sign_up(payload: UserCreate, request: Request, db: Session = Depends(get_db)) -> dict:
    return _sign_up_user(payload, request, db)


@router.post("/signup", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, request: Request, db: Session = Depends(get_db)) -> dict:
    return _sign_up_user(payload, request, db)


def _sign_in_user(payload: UserSignIn, request: Request, db: Session) -> dict:
    enforce_rate_limit(f"auth:signin:ip:{_client_ip(request)}", db=db, limit=30, window_seconds=900)
    enforce_rate_limit(f"auth:signin:email:{payload.email.lower()}", db=db, limit=10, window_seconds=900)
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        record_security_event(
            db,
            action="auth.sign_in",
            result="failure",
            actor_email=payload.email,
            resource_type="user",
            request=request,
            details={"reason": "invalid_credentials"},
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    record_security_event(
        db,
        action="auth.sign_in",
        result="success",
        actor=user,
        resource_type="user",
        resource_id=user.id,
        request=request,
        commit=True,
    )
    return build_auth_response(db, user)


@router.post("/sign-in", response_model=AuthSessionResponse)
def sign_in(payload: UserSignIn, request: Request, db: Session = Depends(get_db)) -> dict:
    return _sign_in_user(payload, request, db)


@router.post("/login", response_model=AuthSessionResponse)
def login(payload: UserSignIn, request: Request, db: Session = Depends(get_db)) -> dict:
    return _sign_in_user(payload, request, db)


@router.get("/me", response_model=UserSummary)
def me(current_user: User = Depends(get_current_user)) -> dict:
    return serialize_user(current_user)


@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    token_payload = getattr(request.state, "auth_payload", {})
    token_jti = token_payload.get("jti")
    if token_jti:
        revoke_auth_session(db, user_id=current_user.id, token_jti=token_jti)
    record_security_event(
        db,
        action="auth.logout",
        result="success",
        actor=current_user,
        resource_type="auth_session",
        resource_id=token_jti,
        request=request,
        commit=True,
    )
    return {"status": "ok"}
