from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models import Deck, User, Workspace
from app.db.session import SessionLocal
from app.services.auth_session_service import is_auth_session_active
from app.services.security_audit_service import record_security_event

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not is_auth_session_active(db, user_id=user.id, token_jti=payload["jti"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or revoked")
    request.state.auth_payload = payload
    return user


def require_roles(*allowed_roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return user

    return dependency


def user_can_access_workspace(user: User, workspace: Workspace) -> bool:
    return user.role == "super_admin" or workspace.user_id == user.id


def user_can_access_deck(user: User, deck: Deck) -> bool:
    if user.role == "super_admin":
        return True
    if deck.user_id == user.id:
        return True
    return bool(deck.workspace and deck.workspace.user_id == user.id)


def get_user_workspace_or_404(db: Session, user: User, workspace_id: str) -> Workspace:
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).one_or_none()
    if workspace is None or not user_can_access_workspace(user, workspace):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


def get_user_deck_or_404(db: Session, user: User, deck_id: str) -> Deck:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None or not user_can_access_deck(user, deck):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return deck


def _audit_super_admin_deck_access(db: Session, request: Request, user: User, deck: Deck) -> None:
    if user.role != "super_admin":
        return

    workspace_owner_id = deck.workspace.user_id if deck.workspace else None
    if deck.user_id == user.id or workspace_owner_id == user.id:
        return

    record_security_event(
        db,
        action="resource.access.super_admin",
        result="success",
        actor=user,
        resource_type="deck",
        resource_id=deck.id,
        request=request,
        details={"deckUserId": deck.user_id, "workspaceUserId": workspace_owner_id},
        commit=True,
    )


def _audit_super_admin_workspace_access(db: Session, request: Request, user: User, workspace: Workspace) -> None:
    if user.role != "super_admin" or workspace.user_id == user.id:
        return

    record_security_event(
        db,
        action="resource.access.super_admin",
        result="success",
        actor=user,
        resource_type="workspace",
        resource_id=workspace.id,
        request=request,
        details={"workspaceUserId": workspace.user_id},
        commit=True,
    )


def require_resource_access(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    deck_id = request.path_params.get("deck_id")
    if isinstance(deck_id, str) and deck_id:
        try:
            deck = get_user_deck_or_404(db, user, deck_id)
            _audit_super_admin_deck_access(db, request, user, deck)
        except HTTPException:
            record_security_event(
                db,
                action="resource.access",
                result="denied",
                actor=user,
                resource_type="deck",
                resource_id=deck_id,
                request=request,
                commit=True,
            )
            raise

    workspace_id = request.path_params.get("workspace_id") or request.query_params.get("workspace_id")
    if isinstance(workspace_id, str) and workspace_id:
        try:
            workspace = get_user_workspace_or_404(db, user, workspace_id)
            _audit_super_admin_workspace_access(db, request, user, workspace)
        except HTTPException:
            record_security_event(
                db,
                action="resource.access",
                result="denied",
                actor=user,
                resource_type="workspace",
                resource_id=workspace_id,
                request=request,
                commit=True,
            )
            raise

    return user
