from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import User
from app.services.rate_limit_service import enforce_rate_limit
from app.services.failure_ticket_service import create_failure_ticket
from app.services.security_audit_service import record_security_event
from app.services.upload_service import attach_limited_upload
from app.services.upload_security import require_supported_deck_upload, stream_limited_upload

router = APIRouter(prefix="/decks", tags=["uploads"])


def _request_path(request: Request | Any) -> str:
    path = getattr(request, "url", None)
    if path is None:
        return ""
    try:
        return str(path.path)
    except AttributeError:
        return str(path)


@router.post("/{deck_id}/upload")
async def upload(
    deck_id: str,
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    enforce_rate_limit(f"upload:user:{current_user.id}", db=db, limit=20, window_seconds=3600)
    file_name = file.filename or "upload.bin"
    content_type = file.content_type or "application/octet-stream"
    upload_file = None
    try:
        require_supported_deck_upload(file_name, content_type)
        upload_file = await stream_limited_upload(file)
        payload = attach_limited_upload(db, deck_id, file_name, content_type, upload_file)
    except HTTPException as exc:
        if upload_file is not None:
            upload_file.path.unlink(missing_ok=True)
        create_failure_ticket(
            db,
            {
                "route": _request_path(request),
                "apiPath": _request_path(request),
                "statusCode": exc.status_code,
                "errorName": exc.__class__.__name__,
                "errorMessage": str(exc.detail),
                "severity": "medium" if exc.status_code < 500 else "high",
                "source": "backend",
                "deckId": deck_id,
                "userId": current_user.id,
                "userEmail": current_user.email,
                "context": {
                    "stage": "upload_receive",
                    "action": "upload",
                    "requestId": getattr(getattr(request, "state", None), "request_id", None),
                },
            },
            request=request,
            current_user=current_user,
            commit=True,
        )
        record_security_event(
            db,
            action="deck.upload",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"contentType": content_type, "fileExtension": Path(file_name).suffix.lower(), "statusCode": exc.status_code},
            commit=True,
        )
        raise
    except ValueError as exc:
        if upload_file is not None:
            upload_file.path.unlink(missing_ok=True)
        create_failure_ticket(
            db,
            {
                "route": _request_path(request),
                "apiPath": _request_path(request),
                "statusCode": 413,
                "errorName": exc.__class__.__name__,
                "errorMessage": str(exc),
                "severity": "medium",
                "source": "backend",
                "deckId": deck_id,
                "userId": current_user.id,
                "userEmail": current_user.email,
                "context": {
                    "stage": "upload_receive",
                    "action": "upload",
                    "requestId": getattr(getattr(request, "state", None), "request_id", None),
                },
            },
            request=request,
            current_user=current_user,
            commit=True,
        )
        record_security_event(
            db,
            action="deck.upload",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"contentType": content_type, "fileExtension": Path(file_name).suffix.lower(), "reason": exc.__class__.__name__},
            commit=True,
        )
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    if payload is None:
        create_failure_ticket(
            db,
            {
                "route": _request_path(request),
                "apiPath": _request_path(request),
                "statusCode": 404,
                "errorName": "LookupError",
                "errorMessage": "Deck not found",
                "severity": "medium",
                "source": "backend",
                "deckId": deck_id,
                "userId": current_user.id,
                "userEmail": current_user.email,
                "context": {
                    "stage": "upload_receive",
                    "action": "upload",
                    "requestId": getattr(getattr(request, "state", None), "request_id", None),
                },
            },
            request=request,
            current_user=current_user,
            commit=True,
        )
        record_security_event(
            db,
            action="deck.upload",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"contentType": content_type, "fileExtension": Path(file_name).suffix.lower(), "statusCode": 404},
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Deck not found")
    record_security_event(
        db,
        action="deck.upload",
        result="success",
        actor=current_user,
        resource_type="deck",
        resource_id=deck_id,
        request=request,
        details={
            "contentType": content_type,
            "fileExtension": Path(file_name).suffix.lower(),
            "size": payload.get("size"),
        },
        commit=True,
    )
    return {"file": payload}
