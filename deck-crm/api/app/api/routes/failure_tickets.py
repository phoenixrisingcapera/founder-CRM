from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import bearer_scheme, get_current_user, get_db, require_roles
from app.core.security import decode_access_token
from app.db.models import User
from app.services.auth_session_service import is_auth_session_active
from app.services.failure_ticket_service import (
    create_failure_ticket,
    get_failure_ticket,
    list_failure_tickets,
    update_failure_ticket,
)

router = APIRouter(prefix="/admin/failure-tickets", tags=["failure-tickets"])


def get_optional_current_user(
    request: Request,
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        return None
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if user is None:
        return None
    if not is_auth_session_active(db, user_id=user.id, token_jti=payload["jti"]):
        return None
    request.state.auth_payload = payload
    return user


@router.post("/report")
def report_failure_ticket(
    request: Request,
    payload: dict = Body(default_factory=dict),
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ticket = create_failure_ticket(db, payload, request=request, current_user=current_user)
    return {"ticketId": ticket.id, "status": "recorded"}


@router.get("", dependencies=[Depends(require_roles("super_admin"))])
def admin_failure_tickets(
    limit: int = Query(default=100, ge=1, le=250),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    source: str | None = Query(default=None),
    deck_id: str | None = Query(default=None, alias="deckId"),
    db: Session = Depends(get_db),
) -> dict:
    return list_failure_tickets(
        db,
        limit=limit,
        status=status,
        severity=severity,
        source=source,
        deck_id=deck_id,
    )


@router.get("/{ticket_id}", dependencies=[Depends(require_roles("super_admin"))])
def admin_failure_ticket_detail(ticket_id: str, db: Session = Depends(get_db)) -> dict:
    detail = get_failure_ticket(db, ticket_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Failure ticket not found.")
    return detail


@router.patch("/{ticket_id}")
def admin_failure_ticket_update(
    ticket_id: str,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        updated = update_failure_ticket(
            db,
            ticket_id,
            status=payload.get("status"),
            admin_notes=payload.get("adminNotes") if "adminNotes" in payload else payload.get("admin_notes"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Failure ticket not found.")
    return updated
