from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.db.models import Company, Contact, Dispatch, FounderWorkspace, IntroPath, Investor, Opportunity, Person, Project, RelationshipEdge
from app.schemas.crm import DeleteResponse
from app.schemas.venture import (
    ActionRecord,
    CompanyCreate,
    CompanyResponse,
    DispatchCreate,
    DispatchResponse,
    IntroPathCreate,
    IntroPathResponse,
    OpportunityCreate,
    OpportunityResponse,
    PersonRecord,
    ProjectCreate,
    ProjectResponse,
    RelationshipEdgeCreate,
    RelationshipEdgeResponse,
    RelationshipGraphEdge,
    RelationshipGraphNode,
    RelationshipGraphResponse,
    RelationshipScoreRecord,
    WarmPathRecord,
)

router = APIRouter(tags=["venture"])


@router.get("/people", response_model=list[PersonRecord])
def list_people(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[PersonRecord]:
    people = db.query(Person).filter(Person.workspace_id == workspace.id).order_by(Person.created_at.desc()).all()
    result: list[PersonRecord] = []
    for person in people:
        contact_type: str | None = None
        investor_stage: str | None = None
        warm_intro_path: str | None = None
        if person.source_kind in ("contact", "both"):
            contact = db.query(Contact).filter(Contact.person_id == person.id).first()
            if contact:
                contact_type = contact.contact_type
        if person.source_kind in ("investor", "both"):
            inv = db.query(Investor).filter(Investor.person_id == person.id).first()
            if inv:
                investor_stage = inv.pipeline_stage
                warm_intro_path = inv.warm_intro_path
        result.append(
            PersonRecord(
                id=person.id,
                name=person.name,
                email=person.email,
                company=person.company,
                relationship_status=person.relationship_status,
                source_kind=person.source_kind,
                contact_type=contact_type,
                investor_stage=investor_stage,
                warm_intro_path=warm_intro_path,
                last_contact_at=person.last_contact_at.isoformat() if person.last_contact_at else None,
                next_follow_up_at=person.next_follow_up_at.isoformat() if person.next_follow_up_at else None,
                created_at=person.created_at.isoformat() if person.created_at else None,
            )
        )
    return result


@router.get("/companies", response_model=list[CompanyResponse])
def list_companies(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[CompanyResponse]:
    rows = db.query(Company).filter(Company.workspace_id == workspace.id).order_by(Company.created_at.desc()).all()
    return [CompanyResponse(id=row.id, name=row.name, website=row.website, company_type=row.company_type, sector=row.sector, geography=row.geography, relationship_summary=row.relationship_summary) for row in rows]


@router.post("/companies", response_model=CompanyResponse)
def create_company(payload: CompanyCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> CompanyResponse:
    row = Company(workspace_id=workspace.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return CompanyResponse(id=row.id, name=row.name, website=row.website, company_type=row.company_type, sector=row.sector, geography=row.geography, relationship_summary=row.relationship_summary)


@router.put("/companies/{company_id}", response_model=CompanyResponse)
def update_company(company_id: str, payload: CompanyCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> CompanyResponse:
    row = db.query(Company).filter(Company.id == company_id, Company.workspace_id == workspace.id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Company not found")
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return CompanyResponse(id=row.id, name=row.name, website=row.website, company_type=row.company_type, sector=row.sector, geography=row.geography, relationship_summary=row.relationship_summary)


@router.delete("/companies/{company_id}", response_model=DeleteResponse)
def delete_company(company_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> DeleteResponse:
    row = db.query(Company).filter(Company.id == company_id, Company.workspace_id == workspace.id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(row)
    db.commit()
    return DeleteResponse(status="deleted")


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[ProjectResponse]:
    rows = db.query(Project).filter(Project.workspace_id == workspace.id).order_by(Project.created_at.desc()).all()
    return [ProjectResponse(id=row.id, title=row.title, goal_type=row.goal_type, status=row.status, summary=row.summary) for row in rows]


@router.post("/projects", response_model=ProjectResponse)
def create_project(payload: ProjectCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> ProjectResponse:
    row = Project(workspace_id=workspace.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ProjectResponse(id=row.id, title=row.title, goal_type=row.goal_type, status=row.status, summary=row.summary)


@router.post("/projects/{project_id}/activate", response_model=dict)
def activate_project(project_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> dict:
    project = db.query(Project).filter(Project.id == project_id, Project.workspace_id == workspace.id).one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    ws = db.query(FounderWorkspace).filter(FounderWorkspace.id == workspace.id).one()
    ws.active_project_id = project.id
    ws.active_raise_name = project.title
    db.commit()
    return {"status": "activated", "project_id": project.id, "project_title": project.title}


@router.post("/projects/deactivate", response_model=dict)
def deactivate_project(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> dict:
    ws = db.query(FounderWorkspace).filter(FounderWorkspace.id == workspace.id).one()
    ws.active_project_id = None
    ws.active_raise_name = None
    db.commit()
    return {"status": "deactivated"}


@router.get("/warm-paths", response_model=list[WarmPathRecord])
def find_warm_paths(target_person_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[WarmPathRecord]:
    target = db.query(Person).filter(Person.id == target_person_id, Person.workspace_id == workspace.id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Target person not found")
    edges = db.query(RelationshipEdge).filter(
        RelationshipEdge.workspace_id == workspace.id,
        RelationshipEdge.target_person_id == target_person_id,
    ).all()
    intro_paths = db.query(IntroPath).filter(
        IntroPath.workspace_id == workspace.id,
        IntroPath.to_person_id == target_person_id,
    ).all()
    existing_intro_from = {p.from_person_id for p in intro_paths}
    result: list[WarmPathRecord] = []
    seen_from: set[str] = set()
    for ip in intro_paths:
        from_person = db.query(Person).filter(Person.id == ip.from_person_id).first()
        if from_person and ip.from_person_id not in seen_from:
            seen_from.add(ip.from_person_id)
            result.append(WarmPathRecord(
                intermediary_person_id=ip.from_person_id,
                intermediary_name=from_person.name,
                intermediary_relationship_status=from_person.relationship_status,
                target_person_id=target_person_id,
                target_name=target.name,
                confidence=ip.confidence,
                path_label=ip.path_label,
                relationship_type="intro_path",
                intro_path_id=ip.id,
            ))
    for edge in edges:
        if edge.source_person_id in seen_from:
            continue
        from_person = db.query(Person).filter(Person.id == edge.source_person_id).first()
        if from_person:
            seen_from.add(edge.source_person_id)
            result.append(WarmPathRecord(
                intermediary_person_id=edge.source_person_id,
                intermediary_name=from_person.name,
                intermediary_relationship_status=from_person.relationship_status,
                target_person_id=target_person_id,
                target_name=target.name,
                confidence="medium" if edge.strength in ("medium", "strong") else "low",
                path_label=f"{from_person.name} → {target.name} ({edge.relationship_type})",
                relationship_type=edge.relationship_type,
                intro_path_id=None,
            ))
    return result


@router.get("/action-queue", response_model=list[ActionRecord])
def get_action_queue(goal_type: str = "raise_funding", workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[ActionRecord]:
    from datetime import datetime, timedelta, timezone
    people = db.query(Person).filter(Person.workspace_id == workspace.id).all()
    intro_paths = db.query(IntroPath).filter(IntroPath.workspace_id == workspace.id).all()
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    recent_dispatches = {
        d.person_id for d in db.query(Dispatch).filter(
            Dispatch.workspace_id == workspace.id,
            Dispatch.created_at >= cutoff,
        ).all() if d.person_id
    }
    result: list[ActionRecord] = []
    for person in people:
        if person.id in recent_dispatches:
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
        if goal_type == "raise_funding" and inv:
            fit += 20; reasons.append("Investor target for funding goal")
        intro_count = sum(1 for path in intro_paths if path.from_person_id == person.id)
        if intro_count:
            proximity += min(intro_count * 10, 20); reasons.append("Known intro paths available")
        total = min(fit + proximity, 100)
        days_since = None
        if person.last_contact_at:
            days_since = (datetime.now(timezone.utc) - person.last_contact_at).days
        suggested = "No contact yet — start the relationship"
        if days_since is not None and days_since > 30:
            suggested = f"Follow up — no contact in {days_since} days"
        elif days_since is not None and days_since > 14:
            suggested = f"Light touch — {days_since} days since last contact"
        elif intro_count > 0:
            suggested = "Intro path available — reach out"
        if total >= 50:
            result.append(ActionRecord(
                person_id=person.id, person_name=person.name,
                organization=person.company or ("Investor" if inv else None),
                total_score=total, reasons=reasons,
                days_since_last_contact=days_since,
                suggested_action=suggested,
                intro_paths_available=intro_count,
            ))
    return sorted(result, key=lambda r: r.total_score, reverse=True)[:10]


@router.get("/dispatches", response_model=list[DispatchResponse])
def list_dispatches(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[DispatchResponse]:
    rows = db.query(Dispatch).filter(Dispatch.workspace_id == workspace.id).order_by(Dispatch.created_at.desc()).all()
    result = []
    for row in rows:
        project_title = None
        person_name = None
        intro_path_label = None
        if row.project_id:
            project = db.query(Project).filter(Project.id == row.project_id).first()
            if project:
                project_title = project.title
        if row.person_id:
            person = db.query(Person).filter(Person.id == row.person_id).first()
            if person:
                person_name = person.name
        if row.intro_path_id:
            ip = db.query(IntroPath).filter(IntroPath.id == row.intro_path_id).first()
            if ip:
                intro_path_label = ip.path_label
        result.append(
            DispatchResponse(
                id=row.id, title=row.title, project_id=row.project_id,
                person_id=row.person_id, intro_path_id=row.intro_path_id,
                channel=row.channel, status=row.status,
                next_step=row.next_step, project_title=project_title,
                person_name=person_name, intro_path_label=intro_path_label,
            )
        )
    return result


@router.post("/dispatches", response_model=DispatchResponse)
def create_dispatch(payload: DispatchCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> DispatchResponse:
    row = Dispatch(workspace_id=workspace.id, **payload.model_dump())
    if payload.intro_path_id:
        intro_path = db.query(IntroPath).filter(
            IntroPath.id == payload.intro_path_id,
            IntroPath.workspace_id == workspace.id,
        ).first()
        if intro_path:
            intro_path.status = "in_flight"
    db.add(row)
    db.commit()
    db.refresh(row)
    project_title = None
    person_name = None
    intro_path_label = None
    if row.project_id:
        project = db.query(Project).filter(Project.id == row.project_id).first()
        if project:
            project_title = project.title
    if row.person_id:
        person = db.query(Person).filter(Person.id == row.person_id).first()
        if person:
            person_name = person.name
    if row.intro_path_id:
        ip = db.query(IntroPath).filter(IntroPath.id == row.intro_path_id).first()
        if ip:
            intro_path_label = ip.path_label
    return DispatchResponse(
        id=row.id, title=row.title, project_id=row.project_id,
        person_id=row.person_id, intro_path_id=row.intro_path_id,
        channel=row.channel, status=row.status,
        next_step=row.next_step, project_title=project_title,
        person_name=person_name, intro_path_label=intro_path_label,
    )


@router.get("/opportunities", response_model=list[OpportunityResponse])
def list_opportunities(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[OpportunityResponse]:
    rows = db.query(Opportunity).filter(Opportunity.workspace_id == workspace.id).order_by(Opportunity.created_at.desc()).all()
    result = []
    for row in rows:
        company_name = None
        person_name = None
        if row.company_id:
            company = db.query(Company).filter(Company.id == row.company_id).first()
            if company:
                company_name = company.name
        if row.person_id:
            person = db.query(Person).filter(Person.id == row.person_id).first()
            if person:
                person_name = person.name
        result.append(
            OpportunityResponse(
                id=row.id, title=row.title, company_id=row.company_id,
                person_id=row.person_id, opportunity_type=row.opportunity_type,
                status=row.status, value_label=row.value_label, notes=row.notes,
                company_name=company_name, person_name=person_name,
            )
        )
    return result


@router.post("/opportunities", response_model=OpportunityResponse)
def create_opportunity(payload: OpportunityCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> OpportunityResponse:
    row = Opportunity(workspace_id=workspace.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    company_name = None
    person_name = None
    if row.company_id:
        company = db.query(Company).filter(Company.id == row.company_id).first()
        if company:
            company_name = company.name
    if row.person_id:
        person = db.query(Person).filter(Person.id == row.person_id).first()
        if person:
            person_name = person.name
    return OpportunityResponse(
        id=row.id, title=row.title, company_id=row.company_id,
        person_id=row.person_id, opportunity_type=row.opportunity_type,
        status=row.status, value_label=row.value_label, notes=row.notes,
        company_name=company_name, person_name=person_name,
    )


@router.get("/relationship-edges", response_model=list[RelationshipEdgeResponse])
def list_relationship_edges(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[RelationshipEdgeResponse]:
    rows = db.query(RelationshipEdge).filter(RelationshipEdge.workspace_id == workspace.id).order_by(RelationshipEdge.created_at.desc()).all()
    return [RelationshipEdgeResponse(id=row.id, source_person_id=row.source_person_id, target_person_id=row.target_person_id, target_company_id=row.target_company_id, relationship_type=row.relationship_type, strength=row.strength, notes=row.notes) for row in rows]


@router.post("/relationship-edges", response_model=RelationshipEdgeResponse)
def create_relationship_edge(payload: RelationshipEdgeCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> RelationshipEdgeResponse:
    row = RelationshipEdge(workspace_id=workspace.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return RelationshipEdgeResponse(id=row.id, source_person_id=row.source_person_id, target_person_id=row.target_person_id, target_company_id=row.target_company_id, relationship_type=row.relationship_type, strength=row.strength, notes=row.notes)


@router.get("/intro-paths", response_model=list[IntroPathResponse])
def list_intro_paths(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[IntroPathResponse]:
    rows = db.query(IntroPath).filter(IntroPath.workspace_id == workspace.id).order_by(IntroPath.created_at.desc()).all()
    return [IntroPathResponse(id=row.id, from_person_id=row.from_person_id, to_person_id=row.to_person_id, path_label=row.path_label, confidence=row.confidence, status=row.status) for row in rows]


@router.post("/intro-paths", response_model=IntroPathResponse)
def create_intro_path(payload: IntroPathCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> IntroPathResponse:
    row = IntroPath(workspace_id=workspace.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return IntroPathResponse(id=row.id, from_person_id=row.from_person_id, to_person_id=row.to_person_id, path_label=row.path_label, confidence=row.confidence, status=row.status)


@router.get("/relationship-fit", response_model=list[RelationshipScoreRecord])
def get_relationship_fit(goal_type: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[RelationshipScoreRecord]:
    people = db.query(Person).filter(Person.workspace_id == workspace.id).all()
    intro_paths = db.query(IntroPath).filter(IntroPath.workspace_id == workspace.id).all()
    scored: list[RelationshipScoreRecord] = []
    for person in people:
        fit = 30
        proximity = 20
        reasons: list[str] = []
        contact = None
        if person.source_kind in ("contact", "both"):
            contact = db.query(Contact).filter(Contact.person_id == person.id).first()
        inv = None
        if person.source_kind in ("investor", "both"):
            inv = db.query(Investor).filter(Investor.person_id == person.id).first()
        if contact and contact.contact_type in {"advisor", "angel", "operator"}:
            fit += 20
            reasons.append("Relevant role for venture goal")
        if person.relationship_status in {"warm", "active"}:
            proximity += 30
            reasons.append("Warm or active relationship")
        if person.company:
            fit += 10
            reasons.append("Has organization context")
        if goal_type == "raise_funding" and inv:
            fit += 20
            reasons.append("Investor target for funding goal")
        if goal_type == "raise_funding" and contact and contact.contact_type in {"angel", "advisor"}:
            fit += 15
            reasons.append("Useful for funding path")
        intro_count = sum(1 for path in intro_paths if path.from_person_id == person.id)
        if intro_count:
            proximity += min(intro_count * 10, 20)
            reasons.append("Known intro paths available")
        organization = person.company
        if inv and not organization:
            organization = "Investor"
        scored.append(
            RelationshipScoreRecord(
                person_id=person.id,
                person_name=person.name,
                organization=organization,
                goal_type=goal_type,
                fit_score=min(fit, 100),
                proximity_score=min(proximity, 100),
                total_score=min(fit + proximity, 100),
                reasons=reasons or ["Base relationship record"],
            )
        )
    return sorted(scored, key=lambda item: item.total_score, reverse=True)


@router.get("/relationship-graph", response_model=RelationshipGraphResponse)
def get_relationship_graph(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> RelationshipGraphResponse:
    people = db.query(Person).filter(Person.workspace_id == workspace.id).all()
    companies = db.query(Company).filter(Company.workspace_id == workspace.id).all()
    relationship_edges = db.query(RelationshipEdge).filter(RelationshipEdge.workspace_id == workspace.id).all()
    intro_paths = db.query(IntroPath).filter(IntroPath.workspace_id == workspace.id).all()
    nodes: list[RelationshipGraphNode] = []
    edges: list[RelationshipGraphEdge] = []
    for company in companies:
        nodes.append(RelationshipGraphNode(id=company.id, label=company.name, kind="company"))
    person_map = {p.id: p for p in people}
    for person in people:
        kind = "investor" if person.source_kind == "investor" else "person"
        nodes.append(RelationshipGraphNode(id=person.id, label=person.name, kind=kind))
        if person.company:
            company = next((item for item in companies if item.name == person.company), None)
            if company is not None:
                edges.append(RelationshipGraphEdge(source=person.id, target=company.id, label="connected_to"))
    for edge in relationship_edges:
        target = edge.target_person_id or edge.target_company_id
        if target:
            edges.append(RelationshipGraphEdge(source=edge.source_person_id, target=target, label=edge.relationship_type))
    for path in intro_paths:
        if path.to_person_id:
            edges.append(RelationshipGraphEdge(source=path.from_person_id, target=path.to_person_id, label="intro_path"))
    return RelationshipGraphResponse(nodes=nodes, edges=edges)
