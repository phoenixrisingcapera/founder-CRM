from pathlib import Path
import json

from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.core.security import generate_id
from app.db.models import Deck, DeckLlmArtifact, User
from app.schemas.analysis import AnalysisFindingsRouteResponse
from app.schemas.deck import DeckCreate, ExportCreate, SlideBlockPatch, SmartEditCreate, SuggestionPatch
from app.schemas.deck_workflow import WorkflowExportRequest
from app.schemas.smart_edit import SmartEditResponse, SmartEditSuggestionRouteResponse
from app.schemas.suggestion import AdaptationSuggestionsRouteResponse
from app.services.deck_service import (
    analyse_deck,
    create_deck,
    get_blocks,
    get_deck,
    get_findings,
    get_slides,
    get_status,
    get_suggestions,
    list_decks,
    patch_block,
    patch_suggestion,
    patch_suggestion_with_audit,
)
from app.services.export_service import export_download_payload, get_export
from app.services.deck_iteration_service import get_deck_iterations
from app.services.final_deck_service import get_compiled_deck, get_latest_compiled_deck, prepare_full_deck
from app.services.ai_usage_quota_service import enforce_ai_generation_quota
from app.services.rate_limit_service import enforce_rate_limit
from app.services.security_audit_service import record_security_event
from app.services.guardrail_client import evaluate_deck_guardrail
from app.services.smart_edit_rate_limit import enforce_smart_edit_quota
from app.services.smart_edit_service import create_smart_edit
from app.services.smart_deck_llm_service import SMART_DECK_ASSISTANT_ARTIFACT_TYPE, load_deck_llm_artifact_payload
from app.services.upload_storage import get_upload_storage, promote_upload
from app.services.deck_workflow_service import WorkflowConflictError, queue_export, queue_source_extraction
from app.services.upload_service import attach_limited_upload, complete_deck_upload, create_deck_upload_url
from app.services.upload_security import require_supported_deck_upload, stream_limited_upload

router = APIRouter(prefix="/decks", tags=["decks"])


@router.get("")
def decks_index(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, list[dict]]:
    return {"decks": list_decks(db, current_user.id, include_all=current_user.role == "super_admin")}


@router.post("")
def decks_create(payload: DeckCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    deck = create_deck(db, payload.model_dump(), current_user.id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return deck




@router.get("/generated/latest")
def decks_latest_generated(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    compiled = get_latest_compiled_deck(
        db,
        user_id=current_user.id,
        include_all=current_user.role == "super_admin",
    )
    if compiled is None:
        return {"latestGeneratedDeck": None}
    return {"latestGeneratedDeck": compiled["featuredCard"], "compiledDeck": compiled}


@router.get("/{deck_id}")
def decks_show(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    deck = get_deck(db, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


@router.post("/{deck_id}/upload-url")
def decks_upload_url(
    deck_id: str,
    request: Request,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    filename = str(payload.get("filename") or payload.get("fileName") or "deck.pdf")
    mime_type = str(payload.get("mimeType") or payload.get("contentType") or "application/octet-stream")
    size_value = payload.get("sizeBytes") if payload.get("sizeBytes") is not None else payload.get("size")
    size = int(size_value) if size_value is not None else None
    try:
        upload = create_deck_upload_url(db, deck_id=deck_id, filename=filename, mime_type=mime_type, size=size)
        record_security_event(
            db,
            action="deck.upload_url.create",
            result="success",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={
                "filename": filename,
                "mimeType": mime_type,
                "size": size,
                "storagePath": upload.get("storagePath"),
                "expiresIn": upload.get("expiresIn"),
            },
            commit=True,
        )
    except LookupError as exc:
        record_security_event(
            db,
            action="deck.upload_url.create",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"reason": "not_found", "filename": filename, "mimeType": mime_type},
            commit=True,
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        record_security_event(
            db,
            action="deck.upload_url.create",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"reason": exc.__class__.__name__, "filename": filename, "mimeType": mime_type},
            commit=True,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        record_security_event(
            db,
            action="deck.upload_url.create",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"reason": exc.__class__.__name__, "filename": filename, "mimeType": mime_type},
            commit=True,
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"upload": upload}


@router.post("/{deck_id}/upload-complete")
def decks_upload_complete(
    deck_id: str,
    request: Request,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    storage_path = str(payload.get("storagePath") or payload.get("storage_path") or "")
    filename = str(payload.get("filename") or payload.get("fileName") or Path(storage_path).name or "deck.pdf")
    mime_type = str(payload.get("mimeType") or payload.get("contentType") or "application/octet-stream")
    size_value = payload.get("sizeBytes") if payload.get("sizeBytes") is not None else payload.get("size")
    size = int(size_value) if size_value is not None else None
    if not storage_path:
        raise HTTPException(status_code=400, detail="storagePath is required")
    try:
        result = complete_deck_upload(
            db,
            deck_id=deck_id,
            storage_path=storage_path,
            filename=filename,
            mime_type=mime_type,
            size=size,
        )
        record_security_event(
            db,
            action="deck.upload_complete",
            result="success",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={
                "filename": filename,
                "mimeType": mime_type,
                "size": size,
                "storagePath": storage_path,
                "object": result.get("object"),
            },
            commit=True,
        )
        return result
    except LookupError as exc:
        record_security_event(
            db,
            action="deck.upload_complete",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"reason": "not_found", "storagePath": storage_path},
            commit=True,
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        record_security_event(
            db,
            action="deck.upload_complete",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"reason": "missing_object", "storagePath": storage_path},
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Uploaded object was not found in storage") from exc
    except ValueError as exc:
        record_security_event(
            db,
            action="deck.upload_complete",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"reason": exc.__class__.__name__, "storagePath": storage_path},
            commit=True,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{deck_id}/process")
def decks_process(
    deck_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    try:
        processing = queue_source_extraction(db, deck_id, requested_by_user_id=current_user.id)
        workflow_job_id = str(processing.get("jobId") or "") if isinstance(processing, dict) else ""
        result = {"processing": processing, "deck": get_deck(db, deck_id)}
        record_security_event(
            db,
            action="deck.processing.queue",
            result="success",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"workflowJobId": workflow_job_id or None},
            commit=True,
        )
        return result
    except ValueError as exc:
        record_security_event(
            db,
            action="deck.processing.queue",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"reason": exc.__class__.__name__},
            commit=True,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{deck_id}/insights")
def decks_insights(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    artifacts = (
        db.query(DeckLlmArtifact)
        .filter(
            DeckLlmArtifact.deck_id == deck_id,
            DeckLlmArtifact.artifact_type == SMART_DECK_ASSISTANT_ARTIFACT_TYPE,
            DeckLlmArtifact.status == "ready",
        )
        .order_by(DeckLlmArtifact.created_at.desc())
        .all()
    )
    insights = []
    for artifact in artifacts:
        payload = load_deck_llm_artifact_payload(artifact)
        insight = payload.get("insight") if isinstance(payload, dict) else {}
        insights.append(
            {
                "id": artifact.id,
                "assistantRunId": payload.get("runId") or artifact.artifact_key,
                "deckId": artifact.deck_id,
                "intentType": payload.get("intentType"),
                "scope": payload.get("scope"),
                "outputType": payload.get("outputType"),
                "title": insight.get("title") if isinstance(insight, dict) else None,
                "summary": artifact.summary,
                "content": insight.get("content", {}) if isinstance(insight, dict) else {},
                "confidence": insight.get("confidence") if isinstance(insight, dict) else None,
                "assumptions": insight.get("assumptions", []) if isinstance(insight, dict) else [],
                "missingEvidence": insight.get("missingEvidence", []) if isinstance(insight, dict) else [],
                "suggestedSlideUpdate": insight.get("suggestedSlideUpdate") if isinstance(insight, dict) else None,
                "recommendedAction": insight.get("recommendedAction") if isinstance(insight, dict) else None,
                "createdAt": artifact.created_at.isoformat(),
            }
        )
    return {"insights": insights}


@router.post("/{deck_id}/insights/{insight_id}/apply-to-slide")
def decks_apply_insight_to_slide(
    deck_id: str,
    insight_id: str,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    artifact = (
        db.query(DeckLlmArtifact)
        .filter(
            DeckLlmArtifact.deck_id == deck_id,
            DeckLlmArtifact.id == insight_id,
            DeckLlmArtifact.artifact_type == SMART_DECK_ASSISTANT_ARTIFACT_TYPE,
            DeckLlmArtifact.status == "ready",
        )
        .first()
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Insight not found")

    artifact_payload = load_deck_llm_artifact_payload(artifact)
    insight = artifact_payload.get("insight") if isinstance(artifact_payload, dict) else {}
    target_slide_id = payload.get("slideId") or payload.get("targetSlideId")
    if target_slide_id:
        slide_ids = {slide.id for slide in artifact.deck.slides}
        if target_slide_id not in slide_ids:
            raise HTTPException(status_code=400, detail="slideId does not belong to this deck")

    application_id = generate_id("artifact")
    application_payload = {
        "insightId": insight_id,
        "assistantRunId": artifact_payload.get("runId") or artifact.artifact_key,
        "targetSlideId": target_slide_id,
        "suggestedSlideUpdate": insight.get("suggestedSlideUpdate") if isinstance(insight, dict) else None,
        "appliedByUserId": current_user.id,
        "notes": payload.get("notes"),
    }
    storage = get_upload_storage()
    storage_path = f"artifacts/decks/{deck_id}/deck_insight_slide_application/{application_id}.json"
    stored = storage.write_bytes(
        storage_path,
        json.dumps(application_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8"),
    )
    try:
        stored = promote_upload(stored)
    except Exception:
        storage.delete(stored.storage_path)
        raise

    application = DeckLlmArtifact(
        id=application_id,
        deck_id=deck_id,
        extraction_run_id=None,
        artifact_type="deck_insight_slide_application",
        artifact_key=f"{insight_id}:{target_slide_id or 'unassigned'}",
        schema_version="deck-insight-application.v1",
        status="ready",
        summary=(
            insight.get("suggestedSlideUpdate")
            if isinstance(insight, dict) and insight.get("suggestedSlideUpdate")
            else artifact.summary
        ),
        payload_json={
            "artifactStorageVersion": "deck-insight-application.v1",
            "storageProvider": stored.provider,
            "storagePath": stored.storage_path,
            "contentType": "application/json",
        },
    )
    db.add(application)
    db.commit()

    return {
        "applied": True,
        "applicationId": application.id,
        "insightId": insight_id,
        "deckId": deck_id,
        "targetSlideId": target_slide_id,
        "storageProvider": stored.provider,
        "storagePath": stored.storage_path,
        "suggestedSlideUpdate": application_payload.get("suggestedSlideUpdate"),
    }


@router.post("/{deck_id}/upload")
async def decks_upload(
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
    upload = None
    try:
        require_supported_deck_upload(file_name, content_type)
        upload = await stream_limited_upload(file)
        payload = attach_limited_upload(db, deck_id, file_name, content_type, upload)
    except HTTPException as exc:
        if upload is not None:
            upload.path.unlink(missing_ok=True)
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
        if upload is not None:
            upload.path.unlink(missing_ok=True)
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


@router.post("/{deck_id}/analyse")
def decks_analyse(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    result = analyse_deck(db, deck_id)
    if not result:
        raise HTTPException(status_code=404, detail="Deck not found")
    return result


@router.post("/{deck_id}/finalize")
def decks_finalize(
    deck_id: str,
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    batch_id = payload.get("batchId")
    if not batch_id:
        raise HTTPException(status_code=400, detail="batchId is required")

    try:
        compiled = prepare_full_deck(
            db,
            deck_id,
            batch_id,
            title=payload.get("title"),
            latest_slide_version_id=payload.get("slideVersionId"),
            created_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if compiled is None:
        raise HTTPException(status_code=404, detail="Deck or batch not found")

    return {
        "deckId": compiled["deckId"],
        "finalDeckId": compiled["compiledDeckId"],
        "compiledDeckId": compiled["compiledDeckId"],
        "latestBatchId": compiled["batchId"],
        "latestSlideVersionId": compiled.get("latestSlideVersionId"),
        "status": compiled["status"],
        "redirectTo": compiled["redirectTo"],
        "featuredCard": compiled["featuredCard"],
        "manifest": compiled["manifest"],
    }


@router.get("/{deck_id}/compiled-decks/{compiled_deck_id}")
def decks_compiled_show(
    deck_id: str,
    compiled_deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    compiled = get_compiled_deck(db, deck_id, compiled_deck_id)
    if compiled is None:
        raise HTTPException(status_code=404, detail="Compiled deck not found")
    return {"compiledDeck": compiled}


@router.get("/{deck_id}/iterations")
def decks_iterations(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    iterations = get_deck_iterations(db, deck_id)
    if iterations is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    return iterations


@router.get("/{deck_id}/status")
def decks_status(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    status = get_status(db, deck_id)
    if not status:
        raise HTTPException(status_code=404, detail="Deck not found")
    return status


@router.get("/{deck_id}/slides")
def decks_slides(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[dict]]:
    get_user_deck_or_404(db, current_user, deck_id)
    return {"slides": get_slides(db, deck_id)}


@router.get("/{deck_id}/slides/{slide_id}/blocks")
def decks_slide_blocks(
    deck_id: str,
    slide_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[dict]]:
    get_user_deck_or_404(db, current_user, deck_id)
    return {"blocks": get_blocks(db, deck_id, slide_id)}


@router.patch("/{deck_id}/blocks/{block_id}")
def decks_patch_block(
    deck_id: str,
    block_id: str,
    payload: SlideBlockPatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    block = patch_block(db, deck_id, block_id, payload.text)
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    return {"block": block}


@router.get("/{deck_id}/findings", response_model=AnalysisFindingsRouteResponse)
def decks_findings(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisFindingsRouteResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    return AnalysisFindingsRouteResponse(findings=get_findings(db, deck_id))


@router.get("/{deck_id}/suggestions", response_model=AdaptationSuggestionsRouteResponse)
def decks_suggestions(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdaptationSuggestionsRouteResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    return AdaptationSuggestionsRouteResponse(suggestions=get_suggestions(db, deck_id))


@router.patch("/{deck_id}/suggestions/{suggestion_id}")
def decks_patch_suggestion(
    deck_id: str,
    suggestion_id: str,
    payload: SuggestionPatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    suggestion = patch_suggestion(db, deck_id, suggestion_id, payload.status, payload.edited_text)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return {"suggestion": suggestion}


@router.post("/{deck_id}/smart-edit", response_model=SmartEditResponse)
def decks_smart_edit(
    deck_id: str,
    payload: SmartEditCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmartEditResponse:
    deck = get_user_deck_or_404(db, current_user, deck_id)
    decision = evaluate_deck_guardrail(
        db=db,
        request=request,
        actor=current_user,
        task_type="smart_edit",
        source="smart_edit",
        deck_id=deck.id,
        workspace_id=deck.workspace_id,
        user_instruction=payload.instruction,
        user_id=current_user.id,
        prompt_preview=payload.instruction,
        commit_events=True,
    )
    if not decision.get("allowed", True):
        record_security_event(
            db,
            action="smart_edit.guardrail_blocked",
            result="blocked",
            actor=current_user,
            resource_type="smart_edit_run",
            resource_id=deck.id,
            request=request,
            details={"taskType": "smart_edit", "riskLevel": decision.get("riskLevel"), "policy": decision.get("policy")},
            commit=True,
        )
        raise HTTPException(status_code=403, detail="Request blocked by safety controls. Please revise your instruction and try again.")
    enforce_smart_edit_quota(f"user:{current_user.id}:deck:{deck_id}")
    enforce_rate_limit(f"smart-edit:user:{current_user.id}", db=db, limit=30, window_seconds=3600)
    enforce_ai_generation_quota(db, current_user)
    try:
        result = create_smart_edit(db, deck_id=deck_id, **payload.model_dump())
    except ValueError as exc:
        db.rollback()
        record_security_event(
            db,
            action="smart_edit.generate",
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
        record_security_event(
            db,
            action="smart_edit.generate",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"reason": exc.__class__.__name__},
            commit=True,
        )
        raise HTTPException(status_code=500, detail="Smart Edit generation failed") from exc
    if result is None:
        record_security_event(
            db,
            action="smart_edit.generate",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=deck_id,
            request=request,
            details={"reason": "not_found"},
            commit=True,
        )
        raise HTTPException(status_code=404, detail="Deck, slide, or block not found")
    record_security_event(
        db,
        action="smart_edit.generate",
        result="success",
        actor=current_user,
        resource_type="smart_edit_run",
        resource_id=result["run"]["id"],
        request=request,
        details={"deckId": deck_id, "slideId": payload.slide_id, "blockId": payload.block_id},
        commit=True,
    )
    return SmartEditResponse(**result)


@router.get("/{deck_id}/smart-edit/{smart_edit_run_id}", response_model=SmartEditSuggestionRouteResponse)
def decks_smart_edit_run(
    deck_id: str,
    smart_edit_run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmartEditSuggestionRouteResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    deck = get_deck(db, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    suggestion = next((item for item in deck["smart_edit_suggestions"] if item["run_id"] == smart_edit_run_id), None)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Smart edit run not found")
    return SmartEditSuggestionRouteResponse(suggestion=suggestion)


@router.patch("/{deck_id}/smart-edit/suggestions/{suggestion_id}")
def decks_patch_smart_edit_suggestion(
    deck_id: str,
    suggestion_id: str,
    payload: SuggestionPatch,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    suggestion = patch_suggestion_with_audit(
        db,
        deck_id,
        suggestion_id,
        payload.status,
        payload.edited_text,
        audit_metadata=_audit_metadata(request),
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return {"suggestion": suggestion}


@router.post("/{deck_id}/export")
def decks_export(
    deck_id: str,
    payload: ExportCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    enforce_rate_limit(f"export:user:{current_user.id}", db=db, limit=30, window_seconds=3600)
    export_type = payload.normalized_type
    if not export_type:
        raise HTTPException(status_code=422, detail="Export type is required")
    workflow_request = WorkflowExportRequest(
        type=export_type,
        idempotencyKey=payload.clientEventId or f"{deck_id}:export:{export_type}",
    )
    try:
        accepted = queue_export(db, deck_id, current_user_id=current_user.id, payload=workflow_request)
    except WorkflowConflictError as exc:
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
        commit=True,
    )
    return {"workflow": accepted}


@router.get("/{deck_id}/exports/{export_id}")
def decks_export_show(
    deck_id: str,
    export_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_user_deck_or_404(db, current_user, deck_id)
    deck_export = get_export(db, deck_id, export_id)
    if deck_export is None:
        raise HTTPException(status_code=404, detail="Export not found")
    return {"export": deck_export}


@router.get("/{deck_id}/exports/{export_id}/download")
def decks_export_download(
    deck_id: str,
    export_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    get_user_deck_or_404(db, current_user, deck_id)
    payload = export_download_payload(db, deck_id, export_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Export not found")
    content, media_type, filename = payload
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _rate_limit_key(deck_id: str, request: Request) -> str:
    host = request.client.host if request.client is not None else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")[:120]
    return f"{deck_id}:{host}:{user_agent}"


def _audit_metadata(request: Request) -> dict:
    return {
        "clientHost": request.client.host if request.client is not None else None,
        "userAgent": request.headers.get("user-agent"),
        "requestPath": str(request.url.path),
    }
