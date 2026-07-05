from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.db.models import User
from app.observability import observability_status
from app.services.admin_operations_service import (
    cancel_admin_agent_run,
    create_admin_agent_run_note,
    discard_admin_design_version,
    get_admin_agent_run_detail,
    get_admin_agent_teams,
    get_admin_deck_slides,
    get_admin_overview,
    get_admin_provider_health,
    get_admin_safety_controls,
    get_admin_quotas,
    list_admin_audit_events,
    list_admin_elements,
    list_admin_agent_runs,
    mark_admin_agent_run_failed,
    retry_admin_agent_run,
)
from app.services.admin_workflow_observability_service import get_admin_deck_workflow_processing
from app.services.admin_deck_repair_service import (
    prepare_smart_deck,
    repair_missing_artifacts,
    requeue_stale_deck_jobs,
    retry_deck_processing,
)
from app.services.smart_deck_readiness_service import get_admin_deck_debug as get_admin_deck_debug_payload
from app.services.agent_learning_memory_service import list_agent_learning_memories
from app.services.agent_regression_service import promote_smart_deck_critique_to_regression_case
from app.services.agent_telemetry_service import (
    get_agent_telemetry_metrics,
    get_agent_telemetry_run_detail,
    list_agent_telemetry_events,
    list_agent_telemetry_failures,
    promote_telemetry_failure_to_learning_memory,
    promote_telemetry_failure_to_regression_case,
)
from app.services.llm_knowledge_service import get_llm_knowledge_health
from app.services.storage_health_service import storage_pipeline_health_check
from app.services.security_audit_service import record_security_event
from app.services.failure_ticket_service import create_failure_ticket, list_smart_deck_failure_events
from app.services.storage_inventory_service import build_storage_inventory, cleanup_orphan_storage_objects, cleanup_stale_pending_decks
from app.services.worker_runtime_status_service import get_latest_worker_heartbeat

router = APIRouter(prefix="/admin", tags=["admin-operations"])


@router.get("/overview", dependencies=[Depends(require_roles("super_admin"))])
def admin_overview(db: Session = Depends(get_db)) -> dict:
    return get_admin_overview(db)


@router.get("/agents/runs", dependencies=[Depends(require_roles("super_admin"))])
def admin_agent_runs(
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(get_db),
) -> dict:
    return list_admin_agent_runs(db, limit=limit)


@router.get("/agents/runs/{run_id}", dependencies=[Depends(require_roles("super_admin"))])
def admin_agent_run_detail(run_id: str, db: Session = Depends(get_db)) -> dict:
    detail = get_admin_agent_run_detail(db, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Admin agent run not found.")
    return detail


@router.get("/learning-memories", dependencies=[Depends(require_roles("super_admin"))])
def admin_learning_memories(
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(get_db),
) -> dict:
    return list_agent_learning_memories(db, limit=limit)


@router.get("/telemetry/events", dependencies=[Depends(require_roles("super_admin"))])
def admin_agent_telemetry_events(
    limit: int = Query(default=100, ge=1, le=250),
    run_id: str | None = Query(default=None, alias="runId"),
    deck_id: str | None = Query(default=None, alias="deckId"),
    run_type: str | None = Query(default=None, alias="runType"),
    status: str | None = Query(default=None),
    event_name: str | None = Query(default=None, alias="eventName"),
    db: Session = Depends(get_db),
) -> dict:
    return list_agent_telemetry_events(
        db,
        limit=limit,
        run_id=run_id,
        deck_id=deck_id,
        run_type=run_type,
        status=status,
        event_name=event_name,
    )


@router.get("/telemetry/runs/{run_id}", dependencies=[Depends(require_roles("super_admin"))])
def admin_agent_telemetry_run_detail(run_id: str, db: Session = Depends(get_db)) -> dict:
    detail = get_agent_telemetry_run_detail(db, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Telemetry run not found.")
    return detail


@router.get("/telemetry/metrics", dependencies=[Depends(require_roles("super_admin"))])
def admin_agent_telemetry_metrics(db: Session = Depends(get_db)) -> dict:
    return get_agent_telemetry_metrics(db)


@router.get("/telemetry/failures", dependencies=[Depends(require_roles("super_admin"))])
def admin_agent_telemetry_failures(
    limit: int = Query(default=100, ge=1, le=250),
    run_type: str | None = Query(default=None, alias="runType"),
    deck_id: str | None = Query(default=None, alias="deckId"),
    db: Session = Depends(get_db),
) -> dict:
    return list_agent_telemetry_failures(db, limit=limit, run_type=run_type, deck_id=deck_id)


@router.get("/telemetry/observability", dependencies=[Depends(require_roles("super_admin"))])
def admin_agent_telemetry_observability() -> dict:
    return observability_status()


@router.get("/smart-deck/failures", dependencies=[Depends(require_roles("super_admin"))])
def admin_smart_deck_failures(
    limit: int = Query(default=100, ge=1, le=250),
    deck_id: str | None = Query(default=None, alias="deckId"),
    db: Session = Depends(get_db),
) -> dict:
    return list_smart_deck_failure_events(db, limit=limit, deck_id=deck_id)


@router.get("/llm-knowledge/health", dependencies=[Depends(require_roles("super_admin"))])
def admin_llm_knowledge_health() -> dict:
    return get_llm_knowledge_health()


@router.get("/storage/health", dependencies=[Depends(require_roles("super_admin"))])
def admin_storage_health(request: Request, current_user: User = Depends(require_roles("super_admin")), db: Session = Depends(get_db)) -> dict:
    result = storage_pipeline_health_check()
    if not result.get("ok"):
        try:
            create_failure_ticket(
                db,
                {
                    "route": str(request.url.path),
                    "apiPath": str(request.url.path),
                    "statusCode": 503,
                    "errorName": "StorageHealthCheckFailed",
                    "errorMessage": "Storage health check failed",
                    "severity": "high",
                    "source": "backend",
                    "deckId": None,
                    "context": result,
                },
                request=request,
                current_user=current_user,
                commit=True,
            )
        except Exception:
            pass
    return result


@router.get("/storage/inventory", dependencies=[Depends(require_roles("super_admin"))])
def admin_storage_inventory(
    prefix: str = Query(default=""),
    db: Session = Depends(get_db),
) -> dict:
    return build_storage_inventory(db, prefix=prefix)


@router.post("/storage/cleanup-orphans")
def admin_storage_cleanup_orphans(
    request: Request,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    execute = payload.get("execute") is True
    confirm = payload.get("confirm") is True
    if execute and not confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required to delete orphan storage objects.")
    result = cleanup_orphan_storage_objects(
        db,
        prefix=str(payload.get("prefix") or ""),
        older_than_days=int(payload.get("olderThanDays") or payload.get("older_than_days") or 7),
        execute=execute,
        limit=int(payload.get("limit") or 100),
    )
    record_security_event(
        db,
        action="admin.storage.cleanup_orphans",
        result="success",
        actor=current_user,
        resource_type="storage",
        request=request,
        details={
            "execute": execute,
            "prefix": result["prefix"],
            "candidateCount": result["candidateCount"],
            "deletedCount": result["deletedCount"],
            "failureCount": result["failureCount"],
        },
        commit=True,
    )
    if result["failureCount"] > 0 or (execute and result["deletedCount"] > 0):
        try:
            create_failure_ticket(
                db,
                {
                    "route": str(request.url.path),
                    "apiPath": str(request.url.path),
                    "statusCode": 207 if execute else 200,
                    "errorName": "StorageCleanupReported",
                    "errorMessage": "Storage cleanup reported candidate failures or deletions.",
                    "severity": "medium",
                    "source": "backend",
                    "context": result,
                },
                request=request,
                current_user=current_user,
                commit=True,
            )
        except Exception:
            pass
    return result


@router.post("/storage/cleanup-pending-decks")
def admin_storage_cleanup_pending_decks(
    request: Request,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    execute = payload.get("execute") is True
    confirm = payload.get("confirm") is True
    if execute and not confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required to delete stale pending decks.")
    result = cleanup_stale_pending_decks(
        db,
        older_than_days=int(payload.get("olderThanDays") or payload.get("older_than_days") or 7),
        execute=execute,
        limit=int(payload.get("limit") or 100),
    )
    record_security_event(
        db,
        action="admin.storage.cleanup_pending_decks",
        result="success",
        actor=current_user,
        resource_type="storage",
        request=request,
        details={
            "execute": execute,
            "candidateCount": result["candidateCount"],
            "deletedCount": result["deletedCount"],
            "failureCount": result["failureCount"],
        },
        commit=True,
    )
    return result


@router.post("/telemetry/failures/{event_id}/promote-learning-memory")
def admin_agent_telemetry_promote_learning_memory(
    event_id: str,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        result = promote_telemetry_failure_to_learning_memory(
            db,
            event_id=event_id,
            actor=current_user,
            note=str(payload.get("note") or ""),
            commit=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Telemetry failure event not found.")
    return result


@router.post("/telemetry/failures/{event_id}/promote-regression")
def admin_agent_telemetry_promote_regression(
    event_id: str,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        result = promote_telemetry_failure_to_regression_case(
            db,
            event_id=event_id,
            actor=current_user,
            note=str(payload.get("note") or ""),
            commit=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Telemetry failure event not found.")
    return result


@router.post("/llm-artifacts/{artifact_id}/promote-regression")
def admin_llm_artifact_promote_regression(
    artifact_id: str,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        result = promote_smart_deck_critique_to_regression_case(
            db,
            artifact_id=artifact_id,
            actor=current_user,
            note=str(payload.get("note") or ""),
            commit=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="LLM artifact not found.")
    return result


@router.get("/agent-teams", dependencies=[Depends(require_roles("super_admin"))])
def admin_agent_teams(db: Session = Depends(get_db)) -> dict:
    return get_admin_agent_teams(db)


@router.post("/agents/runs/{run_id}/notes")
def admin_agent_run_note(
    run_id: str,
    request: Request,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        note = create_admin_agent_run_note(
            db,
            run_id=run_id,
            note=str(payload.get("note") or ""),
            actor=current_user,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if note is None:
        raise HTTPException(status_code=404, detail="Admin agent run not found.")
    return {"note": note}


@router.post("/agents/runs/{run_id}/mark-failed")
def admin_agent_run_mark_failed(
    run_id: str,
    request: Request,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    if payload.get("confirm") is not True:
        raise HTTPException(status_code=400, detail="Confirmation is required to mark a run failed.")

    try:
        result = mark_admin_agent_run_failed(
            db,
            run_id=run_id,
            reason=str(payload.get("reason") or ""),
            actor=current_user,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail="Admin agent run not found.")
    return result


@router.post("/agents/runs/{run_id}/cancel")
def admin_agent_run_cancel(
    run_id: str,
    request: Request,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    if payload.get("confirm") is not True:
        raise HTTPException(status_code=400, detail="Confirmation is required to cancel a run.")

    try:
        result = cancel_admin_agent_run(
            db,
            run_id=run_id,
            reason=str(payload.get("reason") or ""),
            actor=current_user,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail="Admin agent run not found.")
    return result


@router.post("/agents/runs/{run_id}/discard")
def admin_agent_run_discard(
    run_id: str,
    request: Request,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    if payload.get("confirm") is not True:
        raise HTTPException(status_code=400, detail="Confirmation is required to discard a design version.")

    try:
        result = discard_admin_design_version(
            db,
            run_id=run_id,
            reason=str(payload.get("reason") or ""),
            actor=current_user,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail="Design version run not found.")
    return result


@router.post("/agents/runs/{run_id}/retry")
def admin_agent_run_retry(
    run_id: str,
    request: Request,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    if payload.get("confirm") is not True:
        raise HTTPException(status_code=400, detail="Confirmation is required to retry a run.")

    try:
        result = retry_admin_agent_run(
            db,
            run_id=run_id,
            reason=str(payload.get("reason") or ""),
            actor=current_user,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail="Admin agent run not found or retry could not be created.")
    return result


@router.get("/decks/{deck_id}/processing", dependencies=[Depends(require_roles("super_admin"))])
def admin_deck_processing(deck_id: str, db: Session = Depends(get_db)) -> dict:
    processing = get_admin_deck_workflow_processing(db, deck_id)
    if processing is None:
        raise HTTPException(status_code=404, detail="Deck processing state not found.")
    return processing


@router.get("/decks/{deck_id}/workflow-state", dependencies=[Depends(require_roles("super_admin"))])
def admin_deck_workflow_state(deck_id: str, db: Session = Depends(get_db)) -> dict:
    workflow = get_admin_deck_workflow_processing(db, deck_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Deck workflow state not found.")
    return workflow


@router.get("/decks/{deck_id}/debug", dependencies=[Depends(require_roles("super_admin"))])
def admin_deck_debug(deck_id: str, db: Session = Depends(get_db)) -> dict:
    payload = get_admin_deck_debug_payload(db, deck_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Deck debug state not found.")
    return payload


@router.post("/decks/{deck_id}/retry-processing")
def admin_deck_retry_processing(
    deck_id: str,
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    payload = retry_deck_processing(db, deck_id, requested_by_user_id=current_user.id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Deck not found.")
    return payload


@router.post("/decks/{deck_id}/requeue-stale-jobs")
def admin_deck_requeue_stale_jobs(
    deck_id: str,
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    payload = requeue_stale_deck_jobs(db, deck_id, requested_by_user_id=current_user.id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Deck not found.")
    return payload


@router.post("/decks/{deck_id}/prepare-smart-deck")
def admin_deck_prepare_smart_deck(
    deck_id: str,
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    payload = prepare_smart_deck(db, deck_id, requested_by_user_id=current_user.id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Deck not found.")
    return payload


@router.post("/decks/{deck_id}/repair-missing-artifacts")
def admin_deck_repair_missing_artifacts(
    deck_id: str,
    current_user: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> dict:
    payload = repair_missing_artifacts(db, deck_id, requested_by_user_id=current_user.id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Deck not found.")
    return payload


@router.get("/workers/heartbeat", dependencies=[Depends(require_roles("super_admin"))])
def admin_worker_heartbeat(db: Session = Depends(get_db)) -> dict:
    return get_latest_worker_heartbeat(db)


@router.get("/decks/{deck_id}/slides", dependencies=[Depends(require_roles("super_admin"))])
def admin_deck_slides(deck_id: str, db: Session = Depends(get_db)) -> dict:
    slides = get_admin_deck_slides(db, deck_id)
    if slides is None:
        raise HTTPException(status_code=404, detail="Deck slides not found.")
    return slides


@router.get("/elements", dependencies=[Depends(require_roles("super_admin"))])
def admin_elements(
    deck_id: str | None = Query(default=None, alias="deckId"),
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(get_db),
) -> dict:
    return list_admin_elements(db, deck_id=deck_id, limit=limit)


@router.get("/decks/{deck_id}/elements", dependencies=[Depends(require_roles("super_admin"))])
def admin_deck_elements(
    deck_id: str,
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(get_db),
) -> dict:
    return list_admin_elements(db, deck_id=deck_id, limit=limit)


@router.get("/quotas", dependencies=[Depends(require_roles("super_admin"))])
def admin_quotas(
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(get_db),
) -> dict:
    return get_admin_quotas(db, limit=limit)


@router.get("/provider-health", dependencies=[Depends(require_roles("super_admin"))])
def admin_provider_health(
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(get_db),
) -> dict:
    return get_admin_provider_health(db, limit=limit)


@router.get("/safety-controls", dependencies=[Depends(require_roles("super_admin"))])
def admin_safety_controls(db: Session = Depends(get_db)) -> dict:
    return get_admin_safety_controls(db)


@router.get("/audit", dependencies=[Depends(require_roles("super_admin"))])
def admin_audit(
    limit: int = Query(default=100, ge=1, le=250),
    action: str | None = Query(default=None),
    result: str | None = Query(default=None),
    resource_type: str | None = Query(default=None, alias="resourceType"),
    actor: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    return list_admin_audit_events(
        db,
        limit=limit,
        action=action,
        result=result,
        resource_type=resource_type,
        actor=actor,
    )
