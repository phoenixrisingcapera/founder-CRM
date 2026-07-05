from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace, get_db
from app.core.config import settings
from app.core.security import create_signed_artifact_token, decode_signed_artifact_token
from app.db.models import DeckArtifact, User
from app.schemas.settings import ApiKeySaveRequest, SettingsSummaryResponse, SignedArtifactUrlResponse
from app.services.settings import list_user_api_key_summaries, save_user_api_key

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsSummaryResponse)
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SettingsSummaryResponse:
    return SettingsSummaryResponse(exports_enabled=settings.exports_enabled, api_keys=list_user_api_key_summaries(db, user))


@router.put("/settings/api-keys", response_model=SettingsSummaryResponse)
def persist_api_key(payload: ApiKeySaveRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SettingsSummaryResponse:
    if not settings.encryption_key:
        raise HTTPException(status_code=400, detail="Persisted API keys require CRM_ENCRYPTION_KEY. Use session-only keys until configured.")
    save_user_api_key(db, user, payload.provider, payload.api_key)
    return SettingsSummaryResponse(exports_enabled=settings.exports_enabled, api_keys=list_user_api_key_summaries(db, user))


@router.post("/artifacts/{artifact_id}/signed-url", response_model=SignedArtifactUrlResponse)
def create_artifact_signed_url(
    artifact_id: str,
    request: Request,
    workspace=Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> SignedArtifactUrlResponse:
    artifact = db.query(DeckArtifact).filter(DeckArtifact.id == artifact_id, DeckArtifact.workspace_id == workspace.id).one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    token = create_signed_artifact_token(artifact.id)
    return SignedArtifactUrlResponse(artifact_id=artifact.id, download_url=str(request.base_url).rstrip("/") + f"/api/artifacts/download/{token}")


@router.get("/artifacts/download/{token}")
def download_artifact(token: str, db: Session = Depends(get_db)) -> PlainTextResponse:
    try:
        payload = decode_signed_artifact_token(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    artifact = db.query(DeckArtifact).filter(DeckArtifact.id == payload["artifact_id"]).one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    response = PlainTextResponse(artifact.content_markdown)
    response.headers["Content-Disposition"] = f'attachment; filename="{artifact.title.replace(" ", "-").lower()}.md"'
    return response
