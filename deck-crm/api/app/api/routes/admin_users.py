from __future__ import annotations

from secrets import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.config import settings
from app.db.models import AuthSession, Deck, SecurityAuditEvent, User, Workspace, WorkspaceAiProviderSetting
from app.schemas.user import BootstrapUserRoleUpdate, UserCreate, UserRoleUpdate, UserSummary
from app.services.security_audit_service import record_security_event
from app.services.user_service import create_user, list_users, serialize_user, update_user_role

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=list[UserSummary], dependencies=[Depends(require_roles("super_admin"))])
def users_index(db: Session = Depends(get_db)) -> list[dict]:
    return list_users(db)


@router.get("/analytics", dependencies=[Depends(require_roles("super_admin"))])
def users_analytics(db: Session = Depends(get_db)) -> dict:
    role_counts = dict(db.query(User.role, func.count(User.id)).group_by(User.role).all())
    deck_status_counts = dict(db.query(Deck.status, func.count(Deck.id)).group_by(Deck.status).all())
    audit_result_counts = dict(
        db.query(SecurityAuditEvent.result, func.count(SecurityAuditEvent.id))
        .group_by(SecurityAuditEvent.result)
        .all()
    )
    action_counts = [
        {"action": action, "count": count}
        for action, count in (
            db.query(SecurityAuditEvent.action, func.count(SecurityAuditEvent.id))
            .group_by(SecurityAuditEvent.action)
            .order_by(func.count(SecurityAuditEvent.id).desc())
            .limit(12)
            .all()
        )
    ]
    recent_activity = [
        {
            "id": event.id,
            "actorUserId": event.actor_user_id,
            "actorEmail": event.actor_email,
            "action": event.action,
            "result": event.result,
            "resourceType": event.resource_type,
            "resourceId": event.resource_id,
            "sourceIp": event.source_ip,
            "requestId": event.request_id,
            "details": event.details_json,
            "createdAt": event.created_at,
        }
        for event in (
            db.query(SecurityAuditEvent)
            .order_by(SecurityAuditEvent.created_at.desc())
            .limit(50)
            .all()
        )
    ]
    recent_decks = [
        {
            "id": deck.id,
            "title": deck.title,
            "status": deck.status,
            "audience": deck.audience,
            "purpose": deck.purpose,
            "slideCount": deck.slide_count,
            "userId": deck.user_id,
            "workspaceId": deck.workspace_id,
            "createdAt": deck.created_at,
            "updatedAt": deck.updated_at,
        }
        for deck in db.query(Deck).order_by(Deck.created_at.desc()).limit(30).all()
    ]
    recent_users = [
        {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "createdAt": user.created_at,
            "updatedAt": user.updated_at,
        }
        for user in db.query(User).order_by(User.created_at.desc()).limit(30).all()
    ]

    return {
        "summary": {
            "users": db.query(User).count(),
            "workspaces": db.query(Workspace).count(),
            "decks": db.query(Deck).count(),
            "authSessions": db.query(AuthSession).count(),
            "workspaceAiConfigured": (
                db.query(WorkspaceAiProviderSetting)
                .filter(WorkspaceAiProviderSetting.configured_at.isnot(None))
                .count()
            ),
            "auditEvents": db.query(SecurityAuditEvent).count(),
        },
        "roleCounts": role_counts,
        "deckStatusCounts": deck_status_counts,
        "auditResultCounts": audit_result_counts,
        "topActions": action_counts,
        "recentActivity": recent_activity,
        "recentDecks": recent_decks,
        "recentUsers": recent_users,
    }


@router.post("", response_model=UserSummary, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("super_admin"))])
def users_create(
    payload: UserCreate,
    request: Request,
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        user = create_user(db, payload)
    except ValueError as exc:
        record_security_event(
            db,
            action="admin.users_create",
            result="failure",
            actor=current_user,
            actor_email=payload.email,
            resource_type="user",
            request=request,
            details={"createdRole": payload.role, "reason": exc.__class__.__name__},
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_security_event(
        db,
        action="admin.users_create",
        result="success",
        actor=current_user,
        resource_type="user",
        resource_id=user.id,
        request=request,
        details={"createdRole": user.role},
        commit=True,
    )
    return serialize_user(user)


@router.patch("/{user_id}/role", response_model=UserSummary, dependencies=[Depends(require_roles("super_admin"))])
def users_update_role(
    user_id: str,
    payload: UserRoleUpdate,
    request: Request,
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    previous_role = user.role
    updated_user = update_user_role(db, user, payload.role)
    record_security_event(
        db,
        action="admin.users_update_role",
        result="success",
        actor=current_user,
        resource_type="user",
        resource_id=user.id,
        request=request,
        details={"previousRole": previous_role, "newRole": updated_user.role},
        commit=True,
    )
    return serialize_user(updated_user)


@router.post("/bootstrap-role", response_model=UserSummary)
def users_bootstrap_role(
    payload: BootstrapUserRoleUpdate,
    request: Request,
    x_user_admin_bootstrap_token: str = Header(default=""),
    db: Session = Depends(get_db),
) -> dict:
    if not settings.user_admin_bootstrap_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not compare_digest(x_user_admin_bootstrap_token, settings.user_admin_bootstrap_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    previous_role = user.role
    updated_user = update_user_role(db, user, payload.role)
    record_security_event(
        db,
        action="admin.users_bootstrap_role",
        result="success",
        actor_email=payload.email,
        resource_type="user",
        resource_id=user.id,
        request=request,
        details={"previousRole": previous_role, "newRole": updated_user.role},
        commit=True,
    )
    return serialize_user(updated_user)

