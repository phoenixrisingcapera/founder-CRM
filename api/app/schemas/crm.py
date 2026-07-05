from pydantic import BaseModel


class DashboardMetric(BaseModel):
    label: str
    value: int
    tone: str


from app.schemas.venture import ActionRecord


class DashboardSummary(BaseModel):
    workspace_name: str
    active_raise_name: str | None = None
    active_project_id: str | None = None
    active_project_title: str | None = None
    active_goal_type: str | None = None
    metrics: list[DashboardMetric]
    upcoming_follow_ups: list[str]
    suggested_actions: list[ActionRecord] = []
    deck_readiness_score: int
    feature_flags: dict[str, bool]
    latest_goal_score: int | None = None
    latest_goal_score_label: str | None = None
    latest_ai_artifact_id: str | None = None
    latest_ai_artifact_title: str | None = None


class PersonCreate(BaseModel):
    name: str
    email: str | None = None
    company: str | None = None
    role: str | None = None
    relationship_status: str = "new"
    notes: str | None = None
    source_kind: str = "contact"


class PersonResponse(PersonCreate):
    id: str
    last_contact_at: str | None = None
    next_follow_up_at: str | None = None
    created_at: str | None = None


class ContactCreate(BaseModel):
    name: str
    email: str | None = None
    company: str | None = None
    role: str | None = None
    contact_type: str
    relationship_status: str = "new"
    notes: str | None = None


class ContactResponse(ContactCreate):
    id: str
    person_id: str | None = None
    last_contact_at: str | None = None
    next_follow_up_at: str | None = None


class InvestorCreate(BaseModel):
    name: str
    investor_type: str
    preferred_stage: str | None = None
    sector_relevance: str | None = None
    thesis: str | None = None
    check_fit_notes: str | None = None
    warm_intro_path: str | None = None
    risk_flags: str | None = None
    pipeline_stage: str = "target investor list"


class InvestorResponse(InvestorCreate):
    id: str
    person_id: str | None = None
    last_contact_at: str | None = None
    next_follow_up_at: str | None = None


class DeleteResponse(BaseModel):
    status: str
