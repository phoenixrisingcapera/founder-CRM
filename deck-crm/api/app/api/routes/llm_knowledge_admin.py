from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.db.models import User
from app.services.llm_knowledge_service import (
    get_llm_knowledge_health,
    get_llm_knowledge_task_contracts,
    reload_llm_knowledge,
)
from app.services.security_audit_service import record_security_event

router = APIRouter(prefix="/admin/llm-knowledge", tags=["admin-llm-knowledge"])


@router.get("/tasks", dependencies=[Depends(require_roles("super_admin"))])
def admin_llm_knowledge_tasks() -> dict:
    return get_llm_knowledge_task_contracts()


@router.post("/reload")
def admin_llm_knowledge_reload(
    request: Request,
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    health = reload_llm_knowledge()
    record_security_event(
        db,
        action="admin.llm_knowledge.reload",
        result="success" if health.get("status") == "ready" else "degraded",
        actor=current_user,
        resource_type="llm_knowledge",
        request=request,
        details={"status": health.get("status"), "packages": health.get("packages", {})},
        commit=True,
    )
    return health


@router.get("/full-health", dependencies=[Depends(require_roles("super_admin"))])
def admin_llm_knowledge_full_health() -> dict:
    """Alias that exposes the extended health shape beside the legacy endpoint."""

    return get_llm_knowledge_health()
