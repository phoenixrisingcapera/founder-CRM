from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import User
from app.schemas.export import ExportCreate
from app.services.deck_workflow_service import WorkflowConflictError, queue_export
from app.services.export_service import export_download_payload, list_exports
from app.services.product_analytics_service import record_deck_product_event
from app.services.rate_limit_service import enforce_rate_limit
from app.services.security_audit_service import record_security_event
from app.schemas.deck_workflow import WorkflowExportRequest

router = APIRouter(prefix="/decks", tags=["exports"])


@router.get("/{deck_id}/exports")
def exports(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    return {"exports": list_exports(db, deck_id)}


@router.post("/{deck_id}/export")
def export(
    deck_id: str,
    payload: ExportCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    deck = get_user_deck_or_404(db, current_user, deck_id)
    export_type = payload.normalized_type
    if not export_type:
        raise HTTPException(status_code=422, detail="Export type is required")

    record_deck_product_event(
        db,
        event_name="export.generate.started",
        actor=current_user,
        deck=deck,
        request=request,
        surface=payload.sourceSurface or "export_page",
        entity_type="deck",
        entity_id=deck_id,
        session_id=payload.sessionId,
        metadata={
            "exportType": export_type,
            "includeFindings": payload.includeFindings,
            "includeSuggestions": payload.includeSuggestions,
            "includeSmartEdits": payload.includeSmartEdits,
            "includeRejected": payload.includeRejected,
            "clientEventId": payload.clientEventId,
            "metadata": payload.metadata or {},
        },
    )
    enforce_rate_limit(f"export:user:{current_user.id}", db=db, limit=30, window_seconds=3600)
    workflow_request = WorkflowExportRequest(
        type=export_type,
        idempotencyKey=payload.clientEventId or f"{deck_id}:export:{export_type}",
    )
    try:
        accepted = queue_export(db, deck_id, current_user_id=current_user.id, payload=workflow_request)
    except WorkflowConflictError as exc:
        record_deck_product_event(
            db,
            event_name="export.generate.failed",
            actor=current_user,
            deck=deck,
            request=request,
            surface=payload.sourceSurface or "export_page",
            entity_type="deck",
            entity_id=deck_id,
            session_id=payload.sessionId,
            metadata={"exportType": export_type, "reason": exc.code},
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": exc.code,
                "message": exc.message,
                "recoverable": exc.recoverable,
                "nextAction": exc.next_action,
            },
        ) from exc
    record_security_event(
        db,
        action="deck.export",
        result="success",
        actor=current_user,
        resource_type="workflow_job",
        resource_id=accepted["jobId"],
        request=request,
        details={"deckId": deck_id, "exportType": export_type, "workflowJobId": accepted["jobId"]},
        commit=False,
    )
    record_deck_product_event(
        db,
        event_name="export.generate.succeeded",
        actor=current_user,
        deck=deck,
        request=request,
        surface=payload.sourceSurface or "export_page",
        entity_type="workflow_job",
        entity_id=accepted["jobId"],
        session_id=payload.sessionId,
        metadata={
            "exportType": export_type,
            "includeFindings": payload.includeFindings,
            "includeSuggestions": payload.includeSuggestions,
            "includeSmartEdits": payload.includeSmartEdits,
            "includeRejected": payload.includeRejected,
            "workflowJobId": accepted["jobId"],
        },
        commit=True,
    )
    return {"workflow": accepted}


@router.get("/{deck_id}/exports/{export_id}/download")
def download_export(
    deck_id: str,
    export_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    deck = get_user_deck_or_404(db, current_user, deck_id)
    payload = export_download_payload(db, deck_id, export_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Export not found")

    content, media_type, filename = payload
    record_deck_product_event(
        db,
        event_name="export.downloaded",
        actor=current_user,
        deck=deck,
        request=request,
        surface="export_page",
        entity_type="deck_export",
        entity_id=export_id,
        metadata={"filename": filename},
        commit=True,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
