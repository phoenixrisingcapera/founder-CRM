from __future__ import annotations

import logging
import traceback
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.core.config import settings
from app.core.security import generate_id
from app.db.models import Deck, DeckFile, User, Workspace
from app.schemas.deck_processing import SmartDeckProcessingStartResponse
from app.schemas.workspace_summary import FirstDeckUploadResponse
from app.services.deck_workflow_service import queue_source_extraction
from app.services.failure_ticket_service import create_failure_ticket
from app.services.rate_limit_service import enforce_rate_limit
from app.services.security_audit_service import record_security_event
from app.services.upload_readiness_service import get_upload_failure_diagnostic_summary
from app.services.upload_scan_service import scan_upload_path
from app.services.upload_security import require_supported_deck_upload, stream_limited_upload
from app.services.upload_storage import LocalUploadStorage, get_upload_storage, promote_upload

logger = logging.getLogger(__name__)
router = APIRouter(tags=["upload-rescue"])
PRODUCT_API_PREFIX = "/api/products/deck-aistack-codes"


def _workspace_for_user(db: Session, user: User, workspace_id: str | None) -> Workspace:
    query = db.query(Workspace).filter(Workspace.user_id == user.id)
    workspace = query.filter(Workspace.id == workspace_id).first() if workspace_id else query.order_by(Workspace.created_at.asc()).first()
    if workspace is not None:
        return workspace

    display_name = (user.name or user.email or "Deck").split("@")[0].split()[0]
    workspace = Workspace(id=generate_id("ws"), name=f"{display_name}'s Workspace", user_id=user.id)
    db.add(workspace)
    db.flush()
    return workspace


def _safe_filename(filename: str) -> str:
    cleaned = Path(filename).name.strip() or "uploaded-deck.bin"
    safe = "".join(ch if ch.isalnum() or ch in ".-_" else "-" for ch in cleaned).strip(".-")
    return safe[:180] or "uploaded-deck.bin"


def _title_from_filename(filename: str, company_name: str | None) -> str:
    if company_name and company_name.strip():
        return f"{company_name.strip()} deck"
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    return stem or "Uploaded deck"


def _storage_diagnostics() -> dict:
    return {
        "storageBackend": settings.upload_storage_backend,
        "hasStorageBucket": bool(settings.upload_storage_s3_bucket),
        "hasStorageRegion": bool(settings.upload_storage_s3_region),
        "hasStorageEndpoint": bool(settings.upload_storage_s3_endpoint_url),
        "hasRailwayBucketAccessKey": bool(settings.railway_bucket_access_key),
        "hasRailwayBucketSecretKey": bool(settings.railway_bucket_secret_key),
    }


def _upload_warning(exc: Exception, *, warning: str, phase: str, fallback_provider: str | None = None) -> dict:
    payload = {
        "warning": warning,
        "phase": phase,
        "failureCategory": phase,
        "errorName": exc.__class__.__name__,
        "errorMessage": str(exc),
        **_storage_diagnostics(),
    }
    if fallback_provider:
        payload["fallbackProvider"] = fallback_provider
    return payload


def _upload_storage_with_fallback() -> tuple[object, dict | None]:
    try:
        return get_upload_storage(), None
    except Exception as exc:
        warning = _upload_warning(
            exc,
            warning="upload_storage_config_failed_using_local_fallback",
            phase="upload_storage_config",
            fallback_provider="local",
        )
        logger.exception("upload_storage_config_failed_using_local_fallback")
        return LocalUploadStorage(), warning


def _upload_save_diagnostics() -> dict:
    readiness = get_upload_failure_diagnostic_summary()
    return {
        "storageDiagnostics": _storage_diagnostics(),
        "uploadReadiness": readiness,
        "missingRequiredChecks": readiness.get("missingRequiredChecks", []),
        "warningChecks": readiness.get("warningChecks", []),
        "acceptedVariableGroups": readiness.get("acceptedVariableGroups", {}),
    }


def _upload_save_failure_detail(request: Request, exc: Exception, ticket_id: str | None) -> dict:
    return {
        "message": "Deck upload could not be saved by the backend. Check uploadReadiness for missing Railway variables or bucket connectivity.",
        "failureCategory": "deck_upload_save",
        "failurePhase": "upload_rescue_route",
        "errorName": exc.__class__.__name__,
        "requestId": getattr(request.state, "request_id", None),
        "ticketId": ticket_id,
        **_upload_save_diagnostics(),
    }


def _workspace_response(workspace: Workspace, deck: Deck, deck_file: DeckFile) -> dict:
    deck_summary = {
        "id": deck.id,
        "title": deck.title,
        "audience": deck.audience,
        "purpose": deck.purpose,
        "status": deck.status,
        "summary": deck.summary or "Saved original source deck.",
        "created_at": deck.created_at,
        "updated_at": deck.updated_at,
        "slide_count": deck.slide_count,
        "thumbnail_url": None,
        "preview_url": None,
        "first_slide_id": None,
        "original_filename": deck_file.original_filename,
    }
    return {
        "workspace": {"id": workspace.id, "name": workspace.name},
        "deck_count": 1,
        "active_deck_id": deck.id,
        "latest_decks": [deck_summary],
        "processing_deck_count": 0,
        "ready_deck_count": 0,
        "export_count": 0,
        "first_time_templates": [],
    }


def _record_failure_ticket(
    db: Session,
    request: Request,
    current_user: User,
    exc: Exception,
    *,
    file_name: str,
    content_type: str,
) -> str | None:
    try:
        ticket = create_failure_ticket(
            db,
            {
                "apiPath": request.url.path,
                "statusCode": 503,
                "errorName": exc.__class__.__name__,
                "errorMessage": str(exc) or "Deck upload failed before the source file was saved.",
                "errorStack": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                "severity": "critical",
                "source": "backend",
                "context": {
                    "phase": "upload_rescue_route",
                    "failureCategory": "deck_upload_save",
                    "fileName": file_name,
                    "contentType": content_type,
                    "fileExtension": Path(file_name).suffix.lower(),
                    **_storage_diagnostics(),
                    **_upload_save_diagnostics(),
                },
            },
            request=request,
            current_user=current_user,
            commit=True,
        )
        return ticket.id
    except Exception:
        db.rollback()
        return None


@router.post("/products/deck-aistack-codes/decks/{deck_id}/smart-deck/start", response_model=SmartDeckProcessingStartResponse)
def start_smart_deck_processing_enqueue_only(
    deck_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmartDeckProcessingStartResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    enforce_rate_limit(f"smart-deck-start:user:{current_user.id}", db=db, limit=10, window_seconds=3600)

    try:
        processing = queue_source_extraction(db, deck_id, requested_by_user_id=current_user.id)
    except ValueError as exc:
        record_security_event(
            db,
            action="deck.smart_deck_start",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"reason": exc.__class__.__name__},
            commit=True,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        ticket_id = None
        try:
            ticket = create_failure_ticket(
                db,
                {
                    "apiPath": request.url.path,
                    "statusCode": 503,
                    "errorName": exc.__class__.__name__,
                    "errorMessage": str(exc) or "Smart Deck processing could not be enqueued.",
                    "errorStack": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                    "severity": "high",
                    "source": "backend",
                    "deckId": deck_id,
                    "context": {"phase": "manual_smart_deck_enqueue_only"},
                },
                request=request,
                current_user=current_user,
                commit=True,
            )
            ticket_id = ticket.id
        except Exception:
            db.rollback()
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Smart Deck processing could not be enqueued. Check storage, database, and worker logs.",
                "failureCategory": "manual_smart_deck_enqueue",
                "requestId": getattr(request.state, "request_id", None),
                "ticketId": ticket_id,
            },
        ) from exc

    run_status = str(processing.get("status") or "") if isinstance(processing, dict) else ""
    run_phase = str(processing.get("phase") or "") if isinstance(processing, dict) else ""
    next_action = str(processing.get("nextAction") or "") if isinstance(processing, dict) else ""
    if not next_action:
        next_action = "open_smart_deck" if run_phase in {"smart_deck_ready", "preview_ready", "applied", "export_ready"} else "view_processing"
    record_security_event(
        db,
        action="deck.smart_deck_start",
        result="success",
        actor=current_user,
        resource_type="workflow_job",
        resource_id=str(processing.get("jobId") or deck_id) if isinstance(processing, dict) else deck_id,
        request=request,
        details={"deckId": deck_id, "runStatus": run_status, "backgroundStarted": False, "durableWorkerRequired": True},
        commit=True,
    )
    return SmartDeckProcessingStartResponse(
        ok=True,
        deck_id=deck_id,
        workflowId=processing.get("workflowId"),
        workflowPhase=run_phase or None,
        workflowStatus=run_status or "queued",
        workflowJobId=processing.get("jobId"),
        workflowJobType=processing.get("jobType"),
        workflowJobStatus=run_status or "queued",
        status=run_status or "queued",
        state=run_status or "queued",
        deckStatus=run_status or "queued",
        processing={
            "id": processing.get("jobId"),
            "runId": processing.get("jobId"),
            "workflowJobId": processing.get("jobId"),
            "workflowJobType": processing.get("jobType"),
            "workflowJobStatus": run_status or "queued",
            "deckId": deck_id,
            "sourceFileId": None,
            "runType": "workflow_job",
            "status": run_status or "queued",
            "runStatus": run_status or "queued",
            "state": run_status or "queued",
            "stage": run_phase or "source_extraction_queued",
            "stageLabel": (run_phase or "source_extraction_queued").replace("_", " ").title(),
            "nextAction": next_action,
            "attemptCount": None,
            "maxAttempts": None,
            "lockedBy": None,
            "lockedAt": None,
            "heartbeatAt": None,
            "requiresManualReview": False,
            "finalFailureReason": None,
            "slideCount": None,
            "blockCount": None,
            "assetCount": None,
            "errorMessage": None,
            "errorJson": None,
            "metadataJson": None,
            "metricsJson": None,
            "createdAt": None,
            "startedAt": None,
            "completedAt": None,
        },
        background_started=False,
        worker_required=True,
        next_action=next_action,
        processing_status_url=f"{PRODUCT_API_PREFIX}/decks/{deck_id}/workflow-state",
        smart_deck_url=f"/decks/{deck_id}/smart-deck",
    )


@router.post("/products/deck-aistack-codes/decks/upload", response_model=FirstDeckUploadResponse)
async def upload_deck_rescue(
    request: Request,
    deck: UploadFile = File(...),
    workspace_id: str | None = Form(default=None),
    company_name: str | None = Form(default=None),
    website_url: str | None = Form(default=None),
    audience: str | None = Form(default=None),
    purpose: str | None = Form(default=None),
    founder_name: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    team_notes: str | None = Form(default=None),
    linkedin_urls: str | None = Form(default=None),
    supporting_urls: str | None = Form(default=None),
    brand_guide: UploadFile | None = File(default=None),
    logo_file: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FirstDeckUploadResponse:
    file_name = deck.filename or "uploaded-deck.pdf"
    content_type = deck.content_type or "application/octet-stream"
    deck_upload = None

    try:
        require_supported_deck_upload(file_name, content_type)
        deck_upload = await stream_limited_upload(deck)

        workspace = _workspace_for_user(db, current_user, workspace_id)
        deck_id = generate_id("deck")
        upload_id = generate_id("upload")
        stored_filename = f"users/{current_user.id}/decks/{deck_id}/source/{upload_id}/{_safe_filename(file_name)}"

        storage, storage_warning = _upload_storage_with_fallback()
        stored = storage.move_file(deck_upload.path, stored_filename)
        security_scan = scan_upload_path(stored.path)
        if storage_warning is None:
            try:
                stored = promote_upload(stored)
            except Exception as promote_exc:
                storage_warning = _upload_warning(
                    promote_exc,
                    warning="remote_storage_promote_failed_using_local_cache",
                    phase="remote_storage_promote",
                    fallback_provider=stored.provider,
                )
                logger.exception("upload_promote_failed_using_local_cache", extra={"storage_path": stored_filename})

        upload_metadata = {"securityScan": security_scan, "smartDeckProcessing": "manual_start_required"}
        if storage_warning is not None:
            upload_metadata["storageWarning"] = storage_warning

        deck_record = Deck(
            id=deck_id,
            workspace_id=workspace.id,
            user_id=current_user.id,
            title=_title_from_filename(file_name, company_name),
            audience=audience or "Investment Committee",
            purpose=purpose or "Initial diligence review",
            status="uploaded",
            source_type="uploaded_deck",
            summary=f"Saved original source deck {file_name}. Press Create your Smart Deck now to start processing.",
        )
        db.add(deck_record)
        db.flush()

        deck_file = DeckFile(
            id=generate_id("file"),
            deck_id=deck_record.id,
            filename=stored_filename,
            original_filename=file_name,
            file_extension=Path(file_name).suffix.lower().removeprefix("."),
            mime_type=content_type,
            size=deck_upload.size,
            storage_provider=stored.provider,
            storage_path=stored.storage_path,
            checksum_sha256=deck_upload.checksum_sha256,
            metadata_json=upload_metadata,
        )
        db.add(deck_file)
        db.commit()
        db.refresh(deck_record)
        db.refresh(deck_file)

        uploaded_at = deck_file.uploaded_at.isoformat() if deck_file.uploaded_at else None
        payload = {
            "ok": True,
            "deck_id": deck_record.id,
            "filename": file_name,
            "upload_success": True,
            "upload_status": "saved",
            "source_file_status": "saved",
            "original_file_url": None,
            "source_file_name": deck_file.original_filename,
            "source_file_size_bytes": deck_file.size,
            "source_file_mime_type": deck_file.mime_type,
            "source_file_extension": deck_file.file_extension,
            "source_file_display_name": deck_file.original_filename,
            "source_file_uploaded_at": uploaded_at,
            "deck_extraction_status": "queued",
            "ui_state": "uploaded",
            "upload_message": "Uploaded" if storage_warning is None else "Uploaded with storage warning",
            "next_step_message": "Your deck is saved. Press Create your Smart Deck now to start processing.",
            "next_action": "create_smart_deck",
            "create_smart_deck_url": f"{PRODUCT_API_PREFIX}/decks/{deck_record.id}/workflows/source-extraction",
            "processing_status_url": f"{PRODUCT_API_PREFIX}/decks/{deck_record.id}/workflow-state",
            "smart_deck_url": f"/decks/{deck_record.id}/smart-deck",
            "storage_warning": storage_warning,
            "confirmation": None,
            "workspace": _workspace_response(workspace, deck_record, deck_file),
        }
        return FirstDeckUploadResponse(**payload)
    except HTTPException:
        if deck_upload is not None:
            deck_upload.path.unlink(missing_ok=True)
        raise
    except ValueError as exc:
        if deck_upload is not None:
            deck_upload.path.unlink(missing_ok=True)
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        if deck_upload is not None:
            deck_upload.path.unlink(missing_ok=True)
        db.rollback()
        ticket_id = _record_failure_ticket(db, request, current_user, exc, file_name=file_name, content_type=content_type)
        raise HTTPException(
            status_code=503,
            detail=_upload_save_failure_detail(request, exc, ticket_id),
        ) from exc
