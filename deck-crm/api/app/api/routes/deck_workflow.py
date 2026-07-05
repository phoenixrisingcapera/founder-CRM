from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import User
from app.schemas.brand_profile import ExtractDeckBrandRouteResponse
from app.schemas.deck_workflow import (
    DeckWorkflowStateResponse,
    SmartDeckReadinessResponse,
    WorkflowApplyRequest,
    WorkflowCommandAcceptedResponse,
    WorkflowCommandRequest,
    WorkflowExportRequest,
    WorkflowGenerationRequest,
    WorkflowLlmParallelizationRequest,
    WorkflowJobResponse,
    WorkflowSourceExtractionRequest,
)
from app.services.ai_usage_quota_service import enforce_ai_generation_quota
from app.services.brand_enrichment_service import enrich_brand_profile_after_extract
from app.services.brand_extraction_service import extract_deck_brand, get_deck_brand_profile
from app.services.smart_deck_readiness_service import get_smart_deck_readiness
from app.services.deck_workflow_service import (
    WorkflowConflictError,
    get_deck_workflow_state,
    get_workflow_job,
    queue_apply_design_version,
    queue_export,
    queue_llm_parallelization,
    queue_smart_deck_generation,
    queue_source_extraction,
)
from app.services.guardrail_client import evaluate_deck_guardrail
from app.services.rate_limit_service import enforce_rate_limit
from app.services.security_audit_service import record_security_event

router = APIRouter(tags=["deck-workflow"])


def _require_generation_guardrail(*, db: Session, request: Request, current_user: User, deck_id: str, workspace_id: str | None, prompt: str) -> None:
    decision = evaluate_deck_guardrail(
        db=db,
        request=request,
        actor=current_user,
        task_type="smart_deck_generation",
        source="workflow_generation_jobs",
        deck_id=deck_id,
        workspace_id=workspace_id,
        user_instruction=prompt,
        user_id=current_user.id,
        prompt_preview=prompt,
        commit_events=True,
    )
    if decision.get("allowed", True):
        return
    record_security_event(
        db,
        action="workflow.generation.guardrail_blocked",
        result="blocked",
        actor=current_user,
        resource_type="deck",
        resource_id=deck_id,
        request=request,
        details={"taskType": "smart_deck_generation", "policy": decision.get("policy"), "riskLevel": decision.get("riskLevel")},
        commit=True,
    )
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request blocked by safety controls. Please revise your request and try again.")


@router.get("/products/deck-aistack-codes/decks/{deck_id}/workflow-state", response_model=DeckWorkflowStateResponse)
def deck_workflow_state(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeckWorkflowStateResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    payload = get_deck_workflow_state(db, deck_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return DeckWorkflowStateResponse(**payload)


@router.get("/products/deck-aistack-codes/decks/{deck_id}/smart-deck-readiness", response_model=SmartDeckReadinessResponse)
def deck_smart_deck_readiness(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmartDeckReadinessResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    payload = get_smart_deck_readiness(db, deck_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return SmartDeckReadinessResponse(**payload)


@router.post(
    "/products/deck-aistack-codes/decks/{deck_id}/workflow-command",
    response_model=WorkflowCommandAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def deck_workflow_command(
    deck_id: str,
    payload: WorkflowCommandRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkflowCommandAcceptedResponse:
    deck = get_user_deck_or_404(db, current_user, deck_id)
    command = payload.command

    if command in {"start_source_extraction", "start_source_processing", "create_smart_deck", "retry"}:
        enforce_rate_limit(f"workflow-source-extraction:user:{current_user.id}", db=db, limit=10, window_seconds=3600)
        accepted = queue_source_extraction(db, deck_id, requested_by_user_id=current_user.id)
        return WorkflowCommandAcceptedResponse(**accepted)

    if command == "generate_preview":
        if payload.generation is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="generation payload is required for generate_preview.")
        _require_generation_guardrail(
            db=db,
            request=request,
            current_user=current_user,
            deck_id=deck.id,
            workspace_id=deck.workspace_id,
            prompt=payload.generation.prompt,
        )
        enforce_rate_limit(f"workflow-smart-deck-generation:user:{current_user.id}", db=db, limit=10, window_seconds=3600)
        enforce_ai_generation_quota(db, current_user)
        try:
            accepted = queue_smart_deck_generation(db, deck_id, current_user_id=current_user.id, payload=payload.generation)
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
        return WorkflowCommandAcceptedResponse(**accepted)

    if command == "run_llm_parallelization":
        if payload.parallelization is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="parallelization payload is required for run_llm_parallelization.",
            )
        try:
            accepted = queue_llm_parallelization(
                db,
                deck_id,
                current_user_id=current_user.id,
                payload=payload.parallelization,
            )
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
        return WorkflowCommandAcceptedResponse(**accepted)

    if command == "apply_design_version":
        if payload.apply is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="apply payload is required for apply_design_version.")
        try:
            accepted = queue_apply_design_version(db, deck_id, current_user_id=current_user.id, payload=payload.apply)
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
        return WorkflowCommandAcceptedResponse(**accepted)

    if command == "export":
        if payload.export is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="export payload is required for export.")
        enforce_rate_limit(f"workflow-export:user:{current_user.id}", db=db, limit=30, window_seconds=3600)
        try:
            accepted = queue_export(db, deck_id, current_user_id=current_user.id, payload=payload.export)
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
        return WorkflowCommandAcceptedResponse(**accepted)

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported workflow command.")


@router.post(
    "/products/deck-aistack-codes/decks/{deck_id}/smart-deck/prepare",
    response_model=WorkflowCommandAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def prepare_smart_deck_workflow(
    deck_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkflowCommandAcceptedResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    enforce_rate_limit(f"workflow-source-extraction:user:{current_user.id}", db=db, limit=10, window_seconds=3600)
    accepted = queue_source_extraction(db, deck_id, requested_by_user_id=current_user.id)
    return WorkflowCommandAcceptedResponse(**accepted)


@router.post(
    "/products/deck-aistack-codes/decks/{deck_id}/workflows/source-extraction",
    response_model=WorkflowCommandAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_source_extraction_workflow(
    deck_id: str,
    payload: WorkflowSourceExtractionRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkflowCommandAcceptedResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    enforce_rate_limit(f"workflow-source-extraction:user:{current_user.id}", db=db, limit=10, window_seconds=3600)
    accepted = queue_source_extraction(db, deck_id, requested_by_user_id=current_user.id)
    return WorkflowCommandAcceptedResponse(**accepted)


@router.post(
    "/products/deck-aistack-codes/decks/{deck_id}/workflows/brand-extraction",
    response_model=ExtractDeckBrandRouteResponse,
)
async def start_brand_extraction_workflow(
    deck_id: str,
    companyUrl: str | None = Form(default=None),
    logoFile: UploadFile | None = File(default=None),
    brandGuidelinesFile: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExtractDeckBrandRouteResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    try:
        profile = await extract_deck_brand(db, deck_id, companyUrl, logoFile, brandGuidelinesFile)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")

    try:
        enrich_brand_profile_after_extract(db, deck_id)
        enriched_profile = get_deck_brand_profile(db, deck_id)
        if enriched_profile is not None:
            profile = enriched_profile
    except Exception:
        db.rollback()

    return ExtractDeckBrandRouteResponse(brandProfileId=profile.id, brandProfile=profile)


@router.post(
    "/products/deck-aistack-codes/decks/{deck_id}/workflows/smart-deck-generation",
    response_model=WorkflowCommandAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_smart_deck_generation_workflow(
    deck_id: str,
    payload: WorkflowGenerationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkflowCommandAcceptedResponse:
    deck = get_user_deck_or_404(db, current_user, deck_id)
    _require_generation_guardrail(
        db=db,
        request=request,
        current_user=current_user,
        deck_id=deck.id,
        workspace_id=deck.workspace_id,
        prompt=payload.prompt,
    )
    enforce_rate_limit(f"workflow-smart-deck-generation:user:{current_user.id}", db=db, limit=10, window_seconds=3600)
    enforce_ai_generation_quota(db, current_user)
    try:
        accepted = queue_smart_deck_generation(db, deck_id, current_user_id=current_user.id, payload=payload)
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
    return WorkflowCommandAcceptedResponse(**accepted)


@router.post(
    "/products/deck-aistack-codes/decks/{deck_id}/workflows/llm-parallelization",
    response_model=WorkflowCommandAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_llm_parallelization_workflow(
    deck_id: str,
    payload: WorkflowLlmParallelizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkflowCommandAcceptedResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    try:
        accepted = queue_llm_parallelization(db, deck_id, current_user_id=current_user.id, payload=payload)
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
    return WorkflowCommandAcceptedResponse(**accepted)


@router.post(
    "/products/deck-aistack-codes/decks/{deck_id}/workflows/apply-design-version",
    response_model=WorkflowCommandAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_apply_design_version_workflow(
    deck_id: str,
    payload: WorkflowApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkflowCommandAcceptedResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    try:
        accepted = queue_apply_design_version(db, deck_id, current_user_id=current_user.id, payload=payload)
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
    return WorkflowCommandAcceptedResponse(**accepted)


@router.post(
    "/products/deck-aistack-codes/decks/{deck_id}/workflows/export",
    response_model=WorkflowCommandAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_export_workflow(
    deck_id: str,
    payload: WorkflowExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkflowCommandAcceptedResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    enforce_rate_limit(f"workflow-export:user:{current_user.id}", db=db, limit=30, window_seconds=3600)
    try:
        accepted = queue_export(db, deck_id, current_user_id=current_user.id, payload=payload)
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
    return WorkflowCommandAcceptedResponse(**accepted)


@router.get("/workflow-jobs/{job_id}", response_model=WorkflowJobResponse)
def workflow_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkflowJobResponse:
    payload = get_workflow_job(db, job_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow job not found")
    get_user_deck_or_404(db, current_user, payload["deckId"])
    return WorkflowJobResponse(**payload)
