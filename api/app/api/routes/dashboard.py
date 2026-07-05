from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.core.config import settings
from app.db.models import AiArtifact, Company, Contact, Deck, Dispatch, FollowUpTask, GoalScore, IntroPath, Investor, Opportunity, Person, Project
from app.schemas.crm import DashboardMetric, DashboardSummary
from app.schemas.venture import ActionRecord

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(
    workspace=Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    people_count = db.query(Person).filter(Person.workspace_id == workspace.id).count()
    deck_count = db.query(Deck).filter(Deck.workspace_id == workspace.id).count()
    follow_up_count = db.query(FollowUpTask).filter(FollowUpTask.workspace_id == workspace.id).count()
    project_count = db.query(Project).filter(Project.workspace_id == workspace.id).count()
    company_count = db.query(Company).filter(Company.workspace_id == workspace.id).count()
    dispatch_count = db.query(Dispatch).filter(Dispatch.workspace_id == workspace.id).count()
    opportunity_count = db.query(Opportunity).filter(Opportunity.workspace_id == workspace.id).count()
    artifact_count = db.query(AiArtifact).filter(AiArtifact.workspace_id == workspace.id).count()
    readiness = min(100, 35 + deck_count * 20 + people_count * 5)

    active_project_id = workspace.active_project_id
    active_project_title = None
    active_goal_type = None
    if active_project_id:
        proj = db.query(Project).filter(Project.id == active_project_id).first()
        if proj:
            active_project_title = proj.title
            active_goal_type = proj.goal_type

    goal = active_goal_type or "raise_funding"
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    recent_dispatch_person_ids = {
        d.person_id for d in db.query(Dispatch).filter(
            Dispatch.workspace_id == workspace.id,
            Dispatch.created_at >= cutoff,
        ).all() if d.person_id
    }
    people = db.query(Person).filter(Person.workspace_id == workspace.id).all()
    intro_paths = db.query(IntroPath).filter(IntroPath.workspace_id == workspace.id).all()
    suggested: list[ActionRecord] = []
    for person in people:
        if person.id in recent_dispatch_person_ids:
            continue
        fit = 30; proximity = 20; reasons: list[str] = []
        contact = db.query(Contact).filter(Contact.person_id == person.id).first() if person.source_kind in ("contact", "both") else None
        inv = db.query(Investor).filter(Investor.person_id == person.id).first() if person.source_kind in ("investor", "both") else None
        if contact and contact.contact_type in {"advisor", "angel", "operator"}:
            fit += 20; reasons.append("Relevant role for venture goal")
        if person.relationship_status in {"warm", "active"}:
            proximity += 30; reasons.append("Warm or active relationship")
        if person.company:
            fit += 10; reasons.append("Has organization context")
        if goal == "raise_funding" and inv:
            fit += 20; reasons.append("Investor target for funding goal")
        intro_count = sum(1 for path in intro_paths if path.from_person_id == person.id)
        if intro_count:
            proximity += min(intro_count * 10, 20); reasons.append("Known intro paths available")
        total = min(fit + proximity, 100)
        days_since = None
        if person.last_contact_at:
            days_since = (datetime.now(timezone.utc) - person.last_contact_at).days
        suggested_action = "No contact yet — start the relationship"
        if days_since is not None and days_since > 30:
            suggested_action = f"Follow up — no contact in {days_since} days"
        elif days_since is not None and days_since > 14:
            suggested_action = f"Light touch — {days_since} days since last contact"
        elif intro_count > 0:
            suggested_action = "Intro path available — reach out"
        if total >= 50:
            suggested.append(ActionRecord(
                person_id=person.id, person_name=person.name,
                organization=person.company or ("Investor" if inv else None),
                total_score=total, reasons=reasons,
                days_since_last_contact=days_since,
                suggested_action=suggested_action,
                intro_paths_available=intro_count,
            ))
    suggested.sort(key=lambda r: r.total_score, reverse=True)
    latest_score = db.query(GoalScore).filter(GoalScore.workspace_id == workspace.id).order_by(GoalScore.created_at.desc()).first()
    latest_artifact = db.query(AiArtifact).filter(AiArtifact.workspace_id == workspace.id).order_by(AiArtifact.created_at.desc()).first()

    return DashboardSummary(
        workspace_name=workspace.name,
        active_raise_name=workspace.active_raise_name,
        active_project_id=active_project_id,
        active_project_title=active_project_title,
        active_goal_type=active_goal_type,
        metrics=[
            DashboardMetric(label="People", value=people_count, tone="neutral"),
            DashboardMetric(label="Companies", value=company_count, tone="neutral"),
            DashboardMetric(label="Projects", value=project_count, tone="accent"),
            DashboardMetric(label="Dispatches", value=dispatch_count, tone="accent"),
            DashboardMetric(label="Deals & Opportunities", value=opportunity_count, tone="warn"),
            DashboardMetric(label="AI Artifacts", value=artifact_count, tone="accent"),
            DashboardMetric(label="Follow-ups", value=follow_up_count, tone="warn"),
        ],
        upcoming_follow_ups=[],
        suggested_actions=suggested[:5],
        deck_readiness_score=readiness,
        feature_flags={"exports_enabled": settings.exports_enabled},
        latest_goal_score=latest_score.total_score if latest_score else None,
        latest_goal_score_label=latest_score.recommended_next_action if latest_score else None,
        latest_ai_artifact_id=latest_artifact.id if latest_artifact else None,
        latest_ai_artifact_title=latest_artifact.title if latest_artifact else None,
    )
