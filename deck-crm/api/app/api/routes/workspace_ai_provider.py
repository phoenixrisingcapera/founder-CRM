from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.workspace_ai_provider import (
    RevokeWorkspaceAiProviderResponse,
    SaveWorkspaceAiProviderRequest,
    SaveWorkspaceAiProviderResponse,
    WorkspaceAiProviderSummary,
)
from app.services.workspace_ai_provider_service import (
    get_workspace_ai_provider_summary,
    revoke_workspace_ai_provider,
    save_workspace_ai_provider,
)
from app.services.security_audit_service import record_security_event

router = APIRouter(prefix="/settings/workspace/ai-provider", tags=["workspace-ai-provider"])


@router.get("", response_model=WorkspaceAiProviderSummary)
def get_workspace_ai_provider(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceAiProviderSummary:
    return get_workspace_ai_provider_summary(db, current_user.id)


@router.post("", response_model=SaveWorkspaceAiProviderResponse, status_code=status.HTTP_201_CREATED)
def post_workspace_ai_provider(
    payload: SaveWorkspaceAiProviderRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        result = save_workspace_ai_provider(db, current_user.id, payload)
    except ValueError as exc:
        record_security_event(
            db,
            action="workspace_ai_provider.save",
            result="failure",
            actor=current_user,
            resource_type="workspace_ai_provider",
            request=request,
            details={"provider": payload.provider, "preferredModel": payload.preferredModel, "reason": exc.__class__.__name__},
            commit=True,
        )
        raise HTTPException(status_code=400, detail="Workspace AI provider configuration failed") from exc
    record_security_event(
        db,
        action="workspace_ai_provider.save",
        result="skipped" if payload.skipForNow else "success",
        actor=current_user,
        resource_type="workspace_ai_provider",
        request=request,
        details={"provider": payload.provider, "preferredModel": payload.preferredModel, "skipForNow": payload.skipForNow},
        commit=True,
    )
    return result


@router.delete("", response_model=RevokeWorkspaceAiProviderResponse)
def delete_workspace_ai_provider(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    result = revoke_workspace_ai_provider(db, current_user.id)
    record_security_event(
        db,
        action="workspace_ai_provider.revoke",
        result="success" if result["revoked"] else "noop",
        actor=current_user,
        resource_type="workspace_ai_provider",
        request=request,
        details={"revoked": result["revoked"]},
        commit=True,
    )
    return result
