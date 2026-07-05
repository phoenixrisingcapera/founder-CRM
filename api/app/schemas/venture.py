from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str
    website: str | None = None
    company_type: str = "target_company"
    sector: str | None = None
    geography: str | None = None
    relationship_summary: str | None = None


class CompanyResponse(CompanyCreate):
    id: str


class ProjectCreate(BaseModel):
    title: str
    goal_type: str
    status: str = "active"
    summary: str | None = None


class ProjectResponse(ProjectCreate):
    id: str


class DispatchCreate(BaseModel):
    title: str
    project_id: str | None = None
    person_id: str | None = None
    intro_path_id: str | None = None
    channel: str = "email"
    status: str = "draft"
    next_step: str | None = None


class DispatchResponse(DispatchCreate):
    id: str
    project_title: str | None = None
    person_name: str | None = None
    intro_path_label: str | None = None


class OpportunityCreate(BaseModel):
    title: str
    company_id: str | None = None
    person_id: str | None = None
    opportunity_type: str = "funding"
    status: str = "open"
    value_label: str | None = None
    notes: str | None = None


class OpportunityResponse(OpportunityCreate):
    id: str
    company_name: str | None = None
    person_name: str | None = None


class RelationshipScoreRecord(BaseModel):
    person_id: str
    person_name: str
    organization: str | None = None
    goal_type: str
    fit_score: int
    proximity_score: int
    total_score: int
    reasons: list[str]


class RelationshipEdgeCreate(BaseModel):
    source_person_id: str
    target_person_id: str | None = None
    target_company_id: str | None = None
    relationship_type: str = "knows"
    strength: str = "medium"
    notes: str | None = None


class RelationshipEdgeResponse(RelationshipEdgeCreate):
    id: str


class IntroPathCreate(BaseModel):
    from_person_id: str
    to_person_id: str | None = None
    path_label: str
    confidence: str = "medium"
    status: str = "available"


class IntroPathResponse(IntroPathCreate):
    id: str


class PersonRecord(BaseModel):
    id: str
    name: str
    email: str | None = None
    company: str | None = None
    role: str | None = None
    relationship_status: str | None = None
    notes: str | None = None
    source_kind: str
    last_contact_at: str | None = None
    next_follow_up_at: str | None = None
    created_at: str | None = None
    investor_stage: str | None = None
    warm_intro_path: str | None = None
    contact_type: str | None = None


class WarmPathRecord(BaseModel):
    intermediary_person_id: str
    intermediary_name: str
    intermediary_relationship_status: str | None = None
    target_person_id: str
    target_name: str
    confidence: str = "medium"
    path_label: str
    relationship_type: str = "knows"
    intro_path_id: str | None = None


class ActionRecord(BaseModel):
    person_id: str
    person_name: str
    organization: str | None = None
    total_score: int
    reasons: list[str]
    days_since_last_contact: int | None = None
    suggested_action: str
    intro_paths_available: int = 0


class GoalScoreCreate(BaseModel):
    project_id: str
    person_id: str | None = None
    company_id: str | None = None
    opportunity_id: str | None = None


class GoalScoreResponse(BaseModel):
    id: str
    project_id: str
    person_id: str | None = None
    company_id: str | None = None
    opportunity_id: str | None = None
    project_title: str | None = None
    person_name: str | None = None
    company_name: str | None = None
    opportunity_title: str | None = None
    total_score: int
    relationship_strength_score: int
    warm_path_score: int
    sector_fit_score: int
    stage_fit_score: int
    recency_score: int
    confidence_score: int
    reasons: list[str]
    missing_data: list[str]
    recommended_next_action: str
    created_at: str | None = None


class AiArtifactCreate(BaseModel):
    goal_score_id: str
    project_id: str
    person_id: str | None = None
    company_id: str | None = None
    opportunity_id: str | None = None
    instruction: str | None = None
    api_key: str | None = None
    provider: str | None = None


class AiArtifactResponse(BaseModel):
    id: str
    project_id: str
    person_id: str | None = None
    company_id: str | None = None
    opportunity_id: str | None = None
    goal_score_id: str | None = None
    artifact_type: str
    title: str
    content_markdown: str
    project_title: str | None = None
    person_name: str | None = None
    company_name: str | None = None
    opportunity_title: str | None = None
    created_at: str | None = None


class RelationshipGraphNode(BaseModel):
    id: str
    label: str
    kind: str


class RelationshipGraphEdge(BaseModel):
    source: str
    target: str
    label: str


class RelationshipGraphResponse(BaseModel):
    nodes: list[RelationshipGraphNode]
    edges: list[RelationshipGraphEdge]
