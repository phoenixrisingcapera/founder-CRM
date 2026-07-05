import json
from collections.abc import Callable
from time import perf_counter

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models import DeckArtifact, DeckGenerationRun, FailureTicket, FounderWorkspace, TelemetryEvent, User


def create_failure_ticket(
    db: Session,
    *,
    error_message: str,
    route: str | None = None,
    page_url: str | None = None,
    api_path: str | None = None,
    status_code: int | None = None,
    severity: str = "medium",
    source: str = "backend",
    error_name: str | None = None,
    error_stack: str | None = None,
    request_id: str | None = None,
    context: dict[str, object] | None = None,
    user_id: str | None = None,
    workspace_id: str | None = None,
) -> FailureTicket:
    ticket = FailureTicket(
        workspace_id=workspace_id,
        user_id=user_id,
        route=route,
        page_url=page_url,
        api_path=api_path,
        status_code=status_code,
        severity=severity,
        source=source,
        error_name=error_name,
        error_message=error_message,
        error_stack=error_stack,
        request_id=request_id,
        context_json=json.dumps(context or {}),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def create_telemetry_event(
    db: Session,
    *,
    event_name: str,
    event_level: str = "info",
    status: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    latency_ms: int | None = None,
    request_id: str | None = None,
    error_message: str | None = None,
    metadata: dict[str, object] | None = None,
    user_id: str | None = None,
    workspace_id: str | None = None,
    deck_id: str | None = None,
    run_id: str | None = None,
) -> TelemetryEvent:
    event = TelemetryEvent(
        workspace_id=workspace_id,
        user_id=user_id,
        deck_id=deck_id,
        run_id=run_id,
        event_name=event_name,
        event_level=event_level,
        status=status,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
        request_id=request_id,
        error_message=error_message,
        metadata_json=json.dumps(metadata or {}),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


async def observe_request(request: Request, call_next: Callable, session_factory: Callable[[], Session]):
    started_at = perf_counter()
    request_id = request.headers.get("x-request-id")
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        db = session_factory()
        try:
            create_failure_ticket(
                db,
                error_message=str(exc),
                api_path=request.url.path,
                severity="high",
                source="backend",
                error_name=exc.__class__.__name__,
                request_id=request_id,
                context={"method": request.method},
            )
            create_telemetry_event(
                db,
                event_name="api.request.failed",
                event_level="error",
                status="failed",
                latency_ms=int((perf_counter() - started_at) * 1000),
                request_id=request_id,
                error_message=str(exc),
                metadata={"path": request.url.path, "method": request.method},
            )
        finally:
            db.close()
        raise

    db = session_factory()
    try:
        create_telemetry_event(
            db,
            event_name="api.request.completed",
            event_level="info",
            status=str(response.status_code),
            latency_ms=int((perf_counter() - started_at) * 1000),
            request_id=request_id,
            metadata={"path": request.url.path, "method": request.method},
        )
    finally:
        db.close()
    return response


def build_admin_overview(db: Session, workspace: FounderWorkspace) -> dict[str, int]:
    recent_ai_runs = db.query(DeckGenerationRun).filter(DeckGenerationRun.workspace_id == workspace.id).count()
    recent_artifacts = db.query(DeckArtifact).filter(DeckArtifact.workspace_id == workspace.id).count()
    recent_failures = db.query(FailureTicket).filter(FailureTicket.workspace_id == workspace.id).count()
    telemetry_events = db.query(TelemetryEvent).filter(TelemetryEvent.workspace_id == workspace.id).count()
    users = db.query(User).count()
    return {
        "recent_ai_runs": recent_ai_runs,
        "recent_artifacts": recent_artifacts,
        "recent_failures": recent_failures,
        "telemetry_events": telemetry_events,
        "users": users,
    }
