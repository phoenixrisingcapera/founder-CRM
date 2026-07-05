from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_user_deck_or_404
from app.db.models import User
from app.schemas.smart_edit import SmartEditCreate, SmartEditResponse, SmartEditSuggestionRouteResponse
from app.schemas.suggestion import SuggestionPatch
from app.services.deck_service import patch_suggestion_with_audit
from app.services.ai_usage_quota_service import enforce_ai_generation_quota
from app.services.rate_limit_service import enforce_rate_limit
from app.services.failure_ticket_service import create_failure_ticket
from app.services.security_audit_service import record_security_event
from app.services.guardrail_client import evaluate_deck_guardrail
from app.services.smart_edit_rate_limit import enforce_smart_edit_quota
from app.services.smart_edit_service import create_smart_edit, get_smart_edit_run

router = APIRouter(prefix="/decks", tags=["smart-edit"])


@router.post("/{deck_id}/smart-edit", response_model=SmartEditResponse)
def smart_edit(
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
        reason = str(
            decision.get("reason")
            or decision.get("decision")
            or "Request blocked by safety controls."
        )
        severity = "high" if str(decision.get("riskLevel", "medium")).lower() in {"high", "critical"} else "medium"
        try:
            create_failure_ticket(
                db,
                {
                    "route": str(request.url.path),
                    "apiPath": str(request.url.path),
                    "statusCode": 403,
                    "errorName": "GuardrailBlocked",
                    "errorMessage": reason,
                    "severity": severity,
                    "source": "backend",
                    "deckId": deck.id,
                    "userId": current_user.id,
                    "userEmail": current_user.email,
                    "context": {
                        "taskType": "smart_edit",
                        "riskLevel": decision.get("riskLevel"),
                        "policy": decision.get("policy"),
                        "guardrailStatus": decision.get("status"),
                        "decision": decision,
                    },
                },
                request=request,
                current_user=current_user,
                commit=True,
            )
        except Exception:
            pass
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
        raise HTTPException(status_code=403, detail=reason)
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
def smart_edit_run(
    deck_id: str,
    smart_edit_run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmartEditSuggestionRouteResponse:
    get_user_deck_or_404(db, current_user, deck_id)
    result = get_smart_edit_run(db, deck_id, smart_edit_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Smart edit run not found")
    return SmartEditSuggestionRouteResponse(**result)


@router.patch("/{deck_id}/smart-edit/suggestions/{suggestion_id}")
def smart_edit_suggestion_patch(
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
