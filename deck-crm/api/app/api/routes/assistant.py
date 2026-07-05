from __future__ import annotations

import hashlib
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import User
from app.schemas.deck_workflow import WorkflowGenerationRequest
from app.schemas.smart_deck import CreateSmartDeckAssistantRunInput
from app.schemas.smart_deck import CreateSmartDeckGenerationJobInput
from app.schemas.smart_deck import SmartDeckAssistantRunResponse
from app.services.ai_usage_quota_service import enforce_ai_generation_quota
from app.services.agent_telemetry_service import record_agent_event
from app.services.deck_workflow_service import WorkflowConflictError, get_workflow_job as get_workflow_job_contract, queue_smart_deck_generation
from app.services.rate_limit_service import enforce_rate_limit
from app.services.security_audit_service import record_security_event
from app.services.guardrail_client import evaluate_deck_guardrail
from app.services.smart_deck_llm_service import (
    create_smart_deck_assistant_run,
    get_generation_provider_config,
    get_smart_deck_workspace,
    get_smart_deck_assistant_run,
    SmartDeckProviderUnavailableError,
)


router = APIRouter(prefix="/assistant", tags=["assistant"])


AssistantIntentType = Literal[
    "market_size",
    "market_research",
    "financial_projection",
    "competitor_landscape",
    "customer_persona",
    "investor_objections",
    "narrative_flow",
    "slide_critique",
    "due_diligence_risks",
    "missing_evidence",
    "rewrite_for_vc",
    "create_design_version",
]


class CreateAssistantRunInput(BaseModel):
    deckId: str = Field(min_length=1)
    intentType: AssistantIntentType
    scope: Literal["current_slide", "selected_slides", "whole_deck"] = "whole_deck"
    currentSlideId: str | None = None
    selectedSlideIds: list[str] = Field(default_factory=list, max_length=20)
    instruction: str = Field(min_length=1, max_length=4000)
    audience: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_slide_selection(self) -> "CreateAssistantRunInput":
        if len(set(self.selectedSlideIds)) != len(self.selectedSlideIds):
            raise ValueError("selectedSlideIds must not contain duplicates.")
        if self.scope == "current_slide" and not self.currentSlideId:
            raise ValueError("currentSlideId is required when scope is current_slide.")
        if self.scope == "selected_slides" and not self.selectedSlideIds:
            raise ValueError("selectedSlideIds is required when scope is selected_slides.")
        return self

    def selected_slide_ids_for_scope(self) -> list[str]:
        if self.scope == "current_slide":
            return [self.currentSlideId] if self.currentSlideId else []
        if self.scope == "selected_slides":
            return self.selectedSlideIds
        return []


class CreateSlideRedesignRunInput(BaseModel):
    deckId: str = Field(min_length=1)
    scope: Literal["selected_slides", "current_slide", "selected_element"] = "selected_slides"
    selectedSlideIds: list[str] = Field(default_factory=list, max_length=20)
    currentSlideId: str | None = None
    selectedElementId: str | None = Field(default=None, max_length=120)
    instruction: str = Field(min_length=1, max_length=4000)
    intentType: Literal["redesign_slides"] = "redesign_slides"
    outputMode: Literal["editable_slide_versions"] = "editable_slide_versions"
    deckType: str | None = Field(default=None, max_length=40)
    audience: str | None = Field(default=None, max_length=120)
    preferredModel: str | None = Field(default=None, max_length=120)
    selectedSubject: str | None = Field(default=None, max_length=80)
    detectedSubjects: list[dict] | None = Field(default=None, max_length=20)
    actionId: str | None = Field(default=None, max_length=120)
    actionPrompt: str | None = Field(default=None, max_length=4000)
    userPrompt: str | None = Field(default=None, max_length=4000)
    latestBatchId: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_slide_selection(self) -> "CreateSlideRedesignRunInput":
        selected_ids = self.selected_slide_ids_for_scope()
        if not selected_ids:
            raise ValueError("Select one or more slides to redesign.")
        if len(set(selected_ids)) != len(selected_ids):
            raise ValueError("selectedSlideIds must not contain duplicates.")
        return self

    def selected_slide_ids_for_scope(self) -> list[str]:
        if self.scope == "current_slide":
            return [self.currentSlideId] if self.currentSlideId else []
        return self.selectedSlideIds


def _slide_redesign_additional_context(payload: CreateSlideRedesignRunInput) -> str:
    lines = [
        f"Assistant scope: {payload.scope}",
        f"Current source slide: {payload.currentSlideId}" if payload.currentSlideId else "",
        f"Selected generated element: {payload.selectedElementId}" if payload.selectedElementId else "",
        f"Audience override: {payload.audience}" if payload.audience else "",
        f"Deck type: {payload.deckType}" if payload.deckType else "",
        f"Selected subject: {payload.selectedSubject}" if payload.selectedSubject else "",
        f"Action id: {payload.actionId}" if payload.actionId else "",
        f"Action prompt: {payload.actionPrompt}" if payload.actionPrompt else "",
        f"User prompt: {payload.userPrompt}" if payload.userPrompt and payload.userPrompt != payload.instruction else "",
        f"Latest batch id: {payload.latestBatchId}" if payload.latestBatchId else "",
        "Detected subjects: " + ", ".join(
            str(subject.get("subject") or subject.get("id") or subject)
            for subject in (payload.detectedSubjects or [])[:6]
            if isinstance(subject, dict)
        ) if payload.detectedSubjects else "",
        "Output mode: editable slide versions",
    ]
    return "\n".join(line for line in lines if line)


def _slide_redesign_generation_input(payload: CreateSlideRedesignRunInput, selected_ids: list[str]) -> CreateSmartDeckGenerationJobInput:
    return CreateSmartDeckGenerationJobInput(
        prompt=payload.instruction,
        selectedSourceSlideIds=selected_ids,
        additionalContext=_slide_redesign_additional_context(payload),
        deckType=payload.deckType,
        audience=payload.audience,
        preferredModel=payload.preferredModel,
        selectedElementId=payload.selectedElementId,
        selectedSubject=payload.selectedSubject,
        actionId=payload.actionId,
        actionPrompt=payload.actionPrompt,
        userPrompt=payload.userPrompt,
        latestBatchId=payload.latestBatchId,
        detectedSubjects=payload.detectedSubjects,
    )


def _slide_redesign_idempotency_key(payload: CreateSlideRedesignRunInput, selected_ids: list[str]) -> str:
    serialized = json.dumps(
        {
            "deckId": payload.deckId,
            "instruction": payload.instruction,
            "scope": payload.scope,
            "selectedSlideIds": selected_ids,
            "deckType": payload.deckType,
            "audience": payload.audience,
            "preferredModel": payload.preferredModel,
            "selectedElementId": payload.selectedElementId,
            "selectedSubject": payload.selectedSubject,
            "actionId": payload.actionId,
            "actionPrompt": payload.actionPrompt,
            "userPrompt": payload.userPrompt,
            "latestBatchId": payload.latestBatchId,
            "detectedSubjects": payload.detectedSubjects,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"{payload.deckId}:assistant-slide-redesign:{digest}"


def _workflow_job_to_generation_job_payload(
    workflow_job: dict,
    *,
    provider: str,
    model: str | None,
    prompt: str,
    selected_ids: list[str],
) -> dict:
    error = workflow_job.get("error") if isinstance(workflow_job.get("error"), dict) else {}
    status_value = str(workflow_job.get("status") or "queued")
    if status_value.startswith("failed") or status_value in {"blocked", "timed_out"}:
        status_value = "failed"
    return {
        "id": workflow_job.get("jobId"),
        "deckId": workflow_job.get("deckId"),
        "status": status_value,
        "provider": provider,
        "model": model,
        "prompt": prompt,
        "selectedSourceSlideIds": selected_ids,
        "styleId": None,
        "brandProductId": "deck-aistack-codes",
        "errorMessage": error.get("message"),
        "createdAt": workflow_job.get("queuedAt") or workflow_job.get("startedAt"),
        "updatedAt": workflow_job.get("heartbeatAt") or workflow_job.get("startedAt") or workflow_job.get("queuedAt"),
        "completedAt": workflow_job.get("completedAt"),
    }


def _record_slide_redesign_failure(
    db: Session,
    *,
    payload: CreateSlideRedesignRunInput,
    current_user_id: str,
    request_id: str | None,
    run_id: str,
    selected_ids: list[str],
    exc: Exception,
) -> None:
    record_agent_event(
        db,
        event_name="ai.assistant.slide_redesign.failed",
        run_type="assistant_slide_redesign",
        deck_id=payload.deckId,
        user_id=current_user_id,
        run_id=run_id,
        event_level="error",
        status="failed",
        error_category=exc.__class__.__name__,
        error_message=str(exc),
        request_id=request_id,
        metadata={"scope": payload.scope, "selectedSlideCount": len(selected_ids)},
        commit=True,
    )


@router.post("/runs", response_model=SmartDeckAssistantRunResponse)
def create_assistant_run(
    payload: CreateAssistantRunInput,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmartDeckAssistantRunResponse:
    deck = get_user_deck_or_404(db, current_user, payload.deckId)
    decision = evaluate_deck_guardrail(
        db=db,
        request=request,
        actor=current_user,
        task_type="assistant_run",
        source="assistant_run",
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
            action="assistant.run.guardrail_blocked",
            result="blocked",
            actor=current_user,
            resource_type="assistant_run",
            resource_id=deck.id,
            request=request,
            details={"taskType": "assistant_run", "riskLevel": decision.get("riskLevel"), "policy": decision.get("policy")},
            commit=True,
        )
        raise HTTPException(status_code=403, detail="Request blocked by safety controls. Please revise your instruction and try again.")
    enforce_rate_limit(f"assistant-run:user:{current_user.id}", db=db, limit=30, window_seconds=3600)
    enforce_ai_generation_quota(db, current_user)
    try:
        result = create_smart_deck_assistant_run(
            db,
            payload.deckId,
            CreateSmartDeckAssistantRunInput(
                intentType=payload.intentType,
                scope=payload.scope,
                instruction=payload.instruction,
                selectedSourceSlideIds=payload.selected_slide_ids_for_scope(),
                activeSourceSlideId=payload.currentSlideId,
                audience=payload.audience,
                saveInsight=True,
            ),
        )
    except ValueError as exc:
        db.rollback()
        record_security_event(
            db,
            action="assistant.run",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=payload.deckId,
            request=request,
            details={"reason": exc.__class__.__name__, "intentType": payload.intentType},
            commit=True,
        )
        record_agent_event(
            db,
            event_name="ai.assistant.failed",
            run_type="smart_deck_assistant",
            deck_id=payload.deckId,
            user_id=current_user.id,
            event_level="error",
            status="failed",
            error_category=exc.__class__.__name__,
            error_message=str(exc),
            request_id=getattr(getattr(request, "state", None), "request_id", None),
            metadata={"intentType": payload.intentType, "scope": payload.scope},
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        record_security_event(
            db,
            action="assistant.run",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=payload.deckId,
            request=request,
            details={"reason": exc.__class__.__name__, "intentType": payload.intentType},
            commit=True,
        )
        record_agent_event(
            db,
            event_name="ai.assistant.failed",
            run_type="smart_deck_assistant",
            deck_id=payload.deckId,
            user_id=current_user.id,
            event_level="error",
            status="failed",
            error_category=exc.__class__.__name__,
            error_message=str(exc),
            request_id=getattr(getattr(request, "state", None), "request_id", None),
            metadata={"intentType": payload.intentType, "scope": payload.scope},
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Assistant run failed") from exc

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    record_security_event(
        db,
        action="assistant.run",
        result="success",
        actor=current_user,
        resource_type="assistant_run",
        resource_id=result["runId"],
        request=request,
        details={"deckId": payload.deckId, "intentType": payload.intentType},
        commit=True,
    )
    record_agent_event(
        db,
        event_name="ai.assistant.completed",
        run_type="smart_deck_assistant",
        deck_id=payload.deckId,
        user_id=current_user.id,
        run_id=result["runId"],
        status="completed",
        request_id=getattr(getattr(request, "state", None), "request_id", None),
        metadata={
            "intentType": payload.intentType,
            "scope": payload.scope,
            "selectedSlideCount": len(payload.selected_slide_ids_for_scope()),
        },
        commit=True,
    )
    return SmartDeckAssistantRunResponse(**result)


@router.post("/slide-redesign-runs")
def create_slide_redesign_run(
    payload: CreateSlideRedesignRunInput,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    deck = get_user_deck_or_404(db, current_user, payload.deckId)
    instruction = payload.instruction
    decision = evaluate_deck_guardrail(
        db=db,
        request=request,
        actor=current_user,
        task_type="assistant_slide_redesign",
        source="assistant_slide_redesign",
        deck_id=deck.id,
        workspace_id=deck.workspace_id,
        user_instruction=instruction,
        user_id=current_user.id,
        prompt_preview=instruction,
        commit_events=True,
    )
    if not decision.get("allowed", True):
        record_security_event(
            db,
            action="assistant.slide_redesign.guardrail_blocked",
            result="blocked",
            actor=current_user,
            resource_type="generation_job",
            resource_id=deck.id,
            request=request,
            details={"taskType": "assistant_slide_redesign", "riskLevel": decision.get("riskLevel"), "policy": decision.get("policy")},
            commit=True,
        )
        raise HTTPException(status_code=403, detail="Request blocked by safety controls. Please revise your request and try again.")
    enforce_rate_limit(f"assistant-slide-redesign:user:{current_user.id}", db=db, limit=10, window_seconds=3600)
    enforce_ai_generation_quota(db, current_user)
    selected_ids = payload.selected_slide_ids_for_scope()
    generation_input = _slide_redesign_generation_input(payload, selected_ids)
    workflow_request = WorkflowGenerationRequest(
        prompt=payload.instruction,
        selectedSourceSlideIds=list(selected_ids),
        idempotencyKey=_slide_redesign_idempotency_key(payload, selected_ids),
        additionalContext=generation_input.additionalContext,
        deckType=payload.deckType,
        audience=payload.audience,
        preferredModel=payload.preferredModel,
        selectedElementId=payload.selectedElementId,
        selectedSubject=payload.selectedSubject,
        actionId=payload.actionId,
        actionPrompt=payload.actionPrompt,
        userPrompt=payload.userPrompt,
        latestBatchId=payload.latestBatchId,
        detectedSubjects=payload.detectedSubjects,
    )
    try:
        provider_config = get_generation_provider_config(
            db,
            deck,
            payload.preferredModel,
            strict=True,
            use_case="smart_deck",
        )
    except SmartDeckProviderUnavailableError as exc:
        db.rollback()
        record_security_event(
            db,
            action="assistant.slide_redesign",
            result="blocked",
            actor=current_user,
            resource_type="deck",
            resource_id=payload.deckId,
            request=request,
            details={"reason": exc.__class__.__name__, "scope": payload.scope, "code": "provider_not_configured"},
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "provider_not_configured",
                "message": "Connect an AI provider before generating Smart Deck previews.",
                "recoverable": True,
                "nextAction": "configure_provider",
            },
        ) from exc
    try:
        accepted = queue_smart_deck_generation(db, payload.deckId, current_user_id=current_user.id, payload=workflow_request)
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
    try:
        workflow_job = get_workflow_job_contract(db, accepted["jobId"])
        if workflow_job is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Assistant generation failed")
    except HTTPException:
        raise
    except ValueError as exc:
        db.rollback()
        record_security_event(
            db,
            action="assistant.slide_redesign",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=payload.deckId,
            request=request,
            details={"reason": exc.__class__.__name__, "scope": payload.scope},
            commit=True,
        )
        _record_slide_redesign_failure(
            db,
            payload=payload,
            current_user_id=current_user.id,
            request_id=getattr(getattr(request, "state", None), "request_id", None),
            run_id=str(accepted.get("jobId") or ""),
            selected_ids=selected_ids,
            exc=exc,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        record_security_event(
            db,
            action="assistant.slide_redesign",
            result="failure",
            actor=current_user,
            resource_type="deck",
            resource_id=payload.deckId,
            request=request,
            details={"reason": exc.__class__.__name__, "scope": payload.scope},
            commit=True,
        )
        _record_slide_redesign_failure(
            db,
            payload=payload,
            current_user_id=current_user.id,
            request_id=getattr(getattr(request, "state", None), "request_id", None),
            run_id=str(accepted.get("jobId") or ""),
            selected_ids=selected_ids,
            exc=exc,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Assistant generation failed") from exc

    record_security_event(
        db,
        action="assistant.slide_redesign",
        result="success",
        actor=current_user,
        resource_type="workflow_job",
        resource_id=accepted["jobId"],
        request=request,
        details={"deckId": payload.deckId, "scope": payload.scope, "selectedSlideCount": len(selected_ids), "status": "queued"},
        commit=True,
    )
    return {
        "runId": accepted["jobId"],
        "run_id": accepted["jobId"],
        "deckId": payload.deckId,
        "deck_id": payload.deckId,
        "status": "queued",
        "intentType": "redesign_slides",
        "outputMode": "editable_slide_versions",
        "scope": payload.scope,
        "selectedSlideIds": selected_ids,
        "batchId": None,
        "design_version_id": None,
        "state": "queued",
        "changed_slide_ids": [],
        "generated_slides": [],
        "generatedVersionIds": [],
        "generatedVersionCount": 0,
        "generationJob": _workflow_job_to_generation_job_payload(
            workflow_job,
            provider=provider_config["provider"],
            model=provider_config["model"] if provider_config["provider"] in {"anthropic", "openai", "openrouter"} else None,
            prompt=payload.instruction,
            selected_ids=selected_ids,
        ),
        "designVersion": None,
        "workspace": None,
    }


@router.get("/slide-redesign-runs/{run_id}")
def get_slide_redesign_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    workflow_job = get_workflow_job_contract(db, run_id)
    if workflow_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slide redesign run not found")
    get_user_deck_or_404(db, current_user, workflow_job["deckId"])
    input_payload = workflow_job.get("input") if isinstance(workflow_job.get("input"), dict) else {}
    output_payload = workflow_job.get("output") if isinstance(workflow_job.get("output"), dict) else {}
    status_value = str(workflow_job.get("status") or "queued")
    if status_value.startswith("failed") or status_value in {"blocked", "timed_out"}:
        status_value = "failed"
    return {
        "runId": workflow_job["jobId"],
        "run_id": workflow_job["jobId"],
        "deckId": workflow_job["deckId"],
        "deck_id": workflow_job["deckId"],
        "status": status_value,
        "intentType": "redesign_slides",
        "outputMode": "editable_slide_versions",
        "scope": "selected_slides",
        "selectedSlideIds": list(input_payload.get("selectedSourceSlideIds") or []),
        "batchId": output_payload.get("designVersionId"),
        "design_version_id": output_payload.get("designVersionId"),
        "state": "preview" if output_payload.get("designVersionId") else status_value,
        "changed_slide_ids": list(input_payload.get("selectedSourceSlideIds") or []),
        "generated_slides": [],
        "generatedVersionIds": [],
        "generatedVersionCount": int(output_payload.get("generatedVersionCount") or 0),
        "generationJob": _workflow_job_to_generation_job_payload(
            workflow_job,
            provider="workflow",
            model=None,
            prompt=str(input_payload.get("prompt") or ""),
            selected_ids=list(input_payload.get("selectedSourceSlideIds") or []),
        ),
        "designVersion": None,
        "workspace": get_smart_deck_workspace(db, workflow_job["deckId"]),
    }


@router.get("/runs/{run_id}", response_model=SmartDeckAssistantRunResponse)
def get_assistant_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmartDeckAssistantRunResponse:
    result = get_smart_deck_assistant_run(db, run_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assistant run not found")
    get_user_deck_or_404(db, current_user, result["deckId"])
    return SmartDeckAssistantRunResponse(**result)
