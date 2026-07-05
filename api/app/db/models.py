from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import generate_id, utcnow
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FounderWorkspace(Base):
    __tablename__ = "founder_workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    active_raise_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active_project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship()


class Fund(Base):
    __tablename__ = "funds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    name: Mapped[str] = mapped_column(String(255))
    stage_focus: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sector_focus: Mapped[str | None] = mapped_column(String(255), nullable=True)
    check_size: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Person(Base):
    __tablename__ = "people"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    relationship_status: Mapped[str] = mapped_column(String(80), default="new")
    last_contact_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_follow_up_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_kind: Mapped[str] = mapped_column(String(40), default="contact")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_type: Mapped[str] = mapped_column(String(80))
    relationship_status: Mapped[str] = mapped_column(String(80), default="new")
    last_contact_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_follow_up_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Investor(Base):
    __tablename__ = "investors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    fund_id: Mapped[str | None] = mapped_column(ForeignKey("funds.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    investor_type: Mapped[str] = mapped_column(String(80))
    preferred_stage: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sector_relevance: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    check_fit_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    portfolio_overlap: Mapped[str | None] = mapped_column(Text, nullable=True)
    warm_intro_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    pipeline_stage: Mapped[str] = mapped_column(String(80), default="target investor list")
    last_contact_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_follow_up_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)

    fund: Mapped[Fund | None] = relationship()


class PipelineDeal(Base):
    __tablename__ = "pipeline_deals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    stage: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(80), default="active")
    target_raise_amount: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InteractionNote(Base):
    __tablename__ = "interaction_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(80), default="open")
    due_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    name: Mapped[str] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_type: Mapped[str] = mapped_column(String(80), default="target_company")
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    geography: Mapped[str | None] = mapped_column(String(120), nullable=True)
    relationship_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    title: Mapped[str] = mapped_column(String(255))
    goal_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(80), default="active")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Dispatch(Base):
    __tablename__ = "dispatches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    intro_path_id: Mapped[str | None] = mapped_column(ForeignKey("intro_paths.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    channel: Mapped[str] = mapped_column(String(80), default="email")
    status: Mapped[str] = mapped_column(String(80), default="draft")
    next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    opportunity_type: Mapped[str] = mapped_column(String(80), default="funding")
    status: Mapped[str] = mapped_column(String(80), default="open")
    value_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RelationshipEdge(Base):
    __tablename__ = "relationship_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    source_person_id: Mapped[str] = mapped_column(ForeignKey("people.id"))
    target_person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    target_company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    relationship_type: Mapped[str] = mapped_column(String(80), default="knows")
    strength: Mapped[str] = mapped_column(String(40), default="medium")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IntroPath(Base):
    __tablename__ = "intro_paths"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    from_person_id: Mapped[str] = mapped_column(ForeignKey("people.id"))
    to_person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    path_label: Mapped[str] = mapped_column(String(255))
    confidence: Mapped[str] = mapped_column(String(40), default="medium")
    status: Mapped[str] = mapped_column(String(40), default="available")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GoalScore(Base):
    __tablename__ = "goal_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    opportunity_id: Mapped[str | None] = mapped_column(ForeignKey("opportunities.id"), nullable=True)
    total_score: Mapped[int] = mapped_column(Integer)
    relationship_strength_score: Mapped[int] = mapped_column(Integer)
    warm_path_score: Mapped[int] = mapped_column(Integer)
    sector_fit_score: Mapped[int] = mapped_column(Integer)
    stage_fit_score: Mapped[int] = mapped_column(Integer)
    recency_score: Mapped[int] = mapped_column(Integer)
    confidence_score: Mapped[int] = mapped_column(Integer)
    reasons_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_next_action: Mapped[str] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AiArtifact(Base):
    __tablename__ = "ai_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    opportunity_id: Mapped[str | None] = mapped_column(ForeignKey("opportunities.id"), nullable=True)
    goal_score_id: Mapped[str | None] = mapped_column(ForeignKey("goal_scores.id"), nullable=True)
    artifact_type: Mapped[str] = mapped_column(String(80), default="venture_brief")
    title: Mapped[str] = mapped_column(String(255))
    content_markdown: Mapped[str] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    title: Mapped[str] = mapped_column(String(255))
    audience: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(80), default="uploaded")
    source_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DeckSlide(Base):
    __tablename__ = "deck_slides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    deck_id: Mapped[str] = mapped_column(ForeignKey("decks.id"))
    slide_order: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)


class AudienceProfile(Base):
    __tablename__ = "audience_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    code: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)


class DeckGenerationRun(Base):
    __tablename__ = "deck_generation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    deck_id: Mapped[str] = mapped_column(ForeignKey("decks.id"))
    audience_profile_id: Mapped[str | None] = mapped_column(ForeignKey("audience_profiles.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(80), default="completed")
    prompt_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DeckArtifact(Base):
    __tablename__ = "deck_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("founder_workspaces.id"))
    deck_id: Mapped[str] = mapped_column(ForeignKey("decks.id"))
    generation_run_id: Mapped[str] = mapped_column(ForeignKey("deck_generation_runs.id"))
    artifact_type: Mapped[str] = mapped_column(String(80))
    artifact_status: Mapped[str] = mapped_column(String(40), default="draft")
    title: Mapped[str] = mapped_column(String(255))
    content_markdown: Mapped[str] = mapped_column(Text)
    export_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserApiKey(Base):
    __tablename__ = "user_api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(80))
    encrypted_api_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("founder_workspaces.id"), nullable=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    deck_id: Mapped[str | None] = mapped_column(ForeignKey("decks.id"), nullable=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("deck_generation_runs.id"), nullable=True)
    event_name: Mapped[str] = mapped_column(String(120))
    event_level: Mapped[str] = mapped_column(String(40), default="info")
    status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FailureTicket(Base):
    __tablename__ = "failure_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("founder_workspaces.id"), nullable=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    route: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    api_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str] = mapped_column(String(40), default="medium")
    source: Mapped[str] = mapped_column(String(40), default="backend")
    error_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str] = mapped_column(Text)
    error_stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    context_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)
