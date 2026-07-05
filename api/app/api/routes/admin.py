import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace, get_db
from app.core.config import settings
from app.db.models import FailureTicket, TelemetryEvent, User
from app.db.models import DeckGenerationRun
from app.schemas.admin import (
    AdminFailureTicketResponse,
    AdminFailureTicketsResponse,
    AdminMetric,
    AdminOverviewResponse,
    AdminRunResponse,
    AdminRunsResponse,
    AdminProviderHealthSummaryResponse,
    AdminTelemetryEventResponse,
    AdminTelemetryEventsResponse,
    FailureTicketReportRequest,
    ProviderHealthResponse,
)
from app.services.observability import build_admin_overview, create_failure_ticket
from app.services.settings import list_user_api_key_summaries

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview", response_model=AdminOverviewResponse)
def get_admin_overview(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> AdminOverviewResponse:
    summary = build_admin_overview(db, workspace)
    return AdminOverviewResponse(
        summary=[
            AdminMetric(label="Users", value=summary["users"]),
            AdminMetric(label="AI Runs", value=summary["recent_ai_runs"]),
            AdminMetric(label="Artifacts", value=summary["recent_artifacts"]),
            AdminMetric(label="Failures", value=summary["recent_failures"]),
            AdminMetric(label="Telemetry Events", value=summary["telemetry_events"]),
        ],
        recent_failures=summary["recent_failures"],
        recent_ai_runs=summary["recent_ai_runs"],
        recent_artifacts=summary["recent_artifacts"],
    )


@router.get("/telemetry/events", response_model=AdminTelemetryEventsResponse)
def get_telemetry_events(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> AdminTelemetryEventsResponse:
    rows = (
        db.query(TelemetryEvent)
        .filter((TelemetryEvent.workspace_id == workspace.id) | (TelemetryEvent.workspace_id.is_(None)))
        .order_by(TelemetryEvent.created_at.desc())
        .limit(100)
        .all()
    )
    failed = sum(1 for row in rows if row.event_level == "error" or row.status == "failed")
    return AdminTelemetryEventsResponse(
        total=len(rows),
        failed=failed,
        events=[
            AdminTelemetryEventResponse(
                id=row.id,
                event_name=row.event_name,
                event_level=row.event_level,
                status=row.status,
                provider=row.provider,
                model=row.model,
                latency_ms=row.latency_ms,
                request_id=row.request_id,
                error_message=row.error_message,
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        ],
    )


@router.get("/runs", response_model=AdminRunsResponse)
def get_admin_runs(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> AdminRunsResponse:
    rows = (
        db.query(DeckGenerationRun)
        .filter(DeckGenerationRun.workspace_id == workspace.id)
        .order_by(DeckGenerationRun.created_at.desc())
        .limit(100)
        .all()
    )
    return AdminRunsResponse(
        total=len(rows),
        runs=[
            AdminRunResponse(
                id=row.id,
                deck_id=row.deck_id,
                provider=row.provider,
                model=row.model,
                status=row.status,
                prompt_summary=row.prompt_summary,
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        ],
    )


@router.get("/failure-tickets", response_model=AdminFailureTicketsResponse)
def get_failure_tickets(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> AdminFailureTicketsResponse:
    rows = (
        db.query(FailureTicket)
        .filter((FailureTicket.workspace_id == workspace.id) | (FailureTicket.workspace_id.is_(None)))
        .order_by(FailureTicket.created_at.desc())
        .limit(100)
        .all()
    )
    return AdminFailureTicketsResponse(
        total=len(rows),
        tickets=[
            AdminFailureTicketResponse(
                id=row.id,
                route=row.route,
                api_path=row.api_path,
                status_code=row.status_code,
                severity=row.severity,
                source=row.source,
                error_name=row.error_name,
                error_message=row.error_message,
                request_id=row.request_id,
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        ],
    )


@router.post("/failure-tickets/report", response_model=AdminFailureTicketResponse)
def report_failure_ticket(
    payload: FailureTicketReportRequest,
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> AdminFailureTicketResponse:
    ticket = create_failure_ticket(
        db,
        error_message=payload.error_message,
        route=payload.route,
        page_url=payload.page_url,
        api_path=payload.api_path,
        status_code=payload.status_code,
        severity=payload.severity,
        source=payload.source,
        error_name=payload.error_name,
        error_stack=payload.error_stack,
        request_id=payload.request_id,
        context=payload.context,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    return AdminFailureTicketResponse(
        id=ticket.id,
        route=ticket.route,
        api_path=ticket.api_path,
        status_code=ticket.status_code,
        severity=ticket.severity,
        source=ticket.source,
        error_name=ticket.error_name,
        error_message=ticket.error_message,
        request_id=ticket.request_id,
        created_at=ticket.created_at.isoformat(),
    )


@router.get("/provider-health", response_model=AdminProviderHealthSummaryResponse)
def get_provider_health(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminProviderHealthSummaryResponse:
    configured = {item["provider"] for item in list_user_api_key_summaries(db, user)}
    return AdminProviderHealthSummaryResponse(
        providers=[
            ProviderHealthResponse(
                provider="openrouter",
                configured=bool(settings.openrouter_api_key) or "openrouter" in configured,
                source="system_or_user",
            ),
            ProviderHealthResponse(
                provider="openai",
                configured=bool(settings.openai_api_key) or "openai" in configured,
                source="system_or_user",
            ),
        ]
    )
