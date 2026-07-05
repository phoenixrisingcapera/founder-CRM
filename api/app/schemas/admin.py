from pydantic import BaseModel


class AdminMetric(BaseModel):
    label: str
    value: int | float | str


class AdminOverviewResponse(BaseModel):
    summary: list[AdminMetric]
    recent_failures: int
    recent_ai_runs: int
    recent_artifacts: int


class AdminRunResponse(BaseModel):
    id: str
    deck_id: str
    provider: str
    model: str
    status: str
    prompt_summary: str
    created_at: str


class AdminRunsResponse(BaseModel):
    total: int
    runs: list[AdminRunResponse]


class AdminTelemetryEventResponse(BaseModel):
    id: str
    event_name: str
    event_level: str
    status: str | None = None
    provider: str | None = None
    model: str | None = None
    latency_ms: int | None = None
    request_id: str | None = None
    error_message: str | None = None
    created_at: str


class AdminTelemetryEventsResponse(BaseModel):
    total: int
    failed: int
    events: list[AdminTelemetryEventResponse]


class AdminFailureTicketResponse(BaseModel):
    id: str
    route: str | None = None
    api_path: str | None = None
    status_code: int | None = None
    severity: str
    source: str
    error_name: str | None = None
    error_message: str
    request_id: str | None = None
    created_at: str


class AdminFailureTicketsResponse(BaseModel):
    total: int
    tickets: list[AdminFailureTicketResponse]


class FailureTicketReportRequest(BaseModel):
    route: str | None = None
    page_url: str | None = None
    api_path: str | None = None
    status_code: int | None = None
    error_name: str | None = None
    error_message: str
    error_stack: str | None = None
    severity: str = "medium"
    source: str = "frontend"
    request_id: str | None = None
    context: dict[str, object] | None = None


class ProviderHealthResponse(BaseModel):
    provider: str
    configured: bool
    source: str


class AdminProviderHealthSummaryResponse(BaseModel):
    providers: list[ProviderHealthResponse]
