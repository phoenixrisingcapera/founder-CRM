from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.db.models import Investor, Person
from app.schemas.crm import DeleteResponse, InvestorCreate, InvestorResponse

router = APIRouter(prefix="/investors", tags=["investors"])


@router.get("", response_model=list[InvestorResponse])
def list_investors(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[InvestorResponse]:
    records = db.query(Investor).filter(Investor.workspace_id == workspace.id).order_by(Investor.created_at.desc()).all()
    return [
        InvestorResponse(
            id=item.id,
            person_id=item.person_id,
            name=item.name,
            investor_type=item.investor_type,
            preferred_stage=item.preferred_stage,
            sector_relevance=item.sector_relevance,
            thesis=item.thesis,
            check_fit_notes=item.check_fit_notes,
            warm_intro_path=item.warm_intro_path,
            risk_flags=item.risk_flags,
            pipeline_stage=item.pipeline_stage,
            last_contact_at=item.last_contact_at.isoformat() if item.last_contact_at else None,
            next_follow_up_at=item.next_follow_up_at.isoformat() if item.next_follow_up_at else None,
        )
        for item in records
    ]


@router.post("", response_model=InvestorResponse)
def create_investor(
    payload: InvestorCreate,
    workspace=Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> InvestorResponse:
    person = Person(workspace_id=workspace.id, name=payload.name,
                    source_kind="investor",
                    relationship_status="new")
    db.add(person)
    db.flush()
    record = Investor(workspace_id=workspace.id, person_id=person.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return InvestorResponse(
        id=record.id,
        person_id=record.person_id,
        name=record.name,
        investor_type=record.investor_type,
        preferred_stage=record.preferred_stage,
        sector_relevance=record.sector_relevance,
        thesis=record.thesis,
        check_fit_notes=record.check_fit_notes,
        warm_intro_path=record.warm_intro_path,
        risk_flags=record.risk_flags,
        pipeline_stage=record.pipeline_stage,
        last_contact_at=None,
        next_follow_up_at=None,
    )


@router.put("/{investor_id}", response_model=InvestorResponse)
def update_investor(investor_id: str, payload: InvestorCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> InvestorResponse:
    record = db.query(Investor).filter(Investor.id == investor_id, Investor.workspace_id == workspace.id).one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Investor not found")
    for field, value in payload.model_dump().items():
        setattr(record, field, value)
    if record.person_id:
        person = db.query(Person).filter(Person.id == record.person_id).one_or_none()
        if person:
            person.name = record.name
    db.commit()
    db.refresh(record)
    return InvestorResponse(
        id=record.id,
        person_id=record.person_id,
        name=record.name,
        investor_type=record.investor_type,
        preferred_stage=record.preferred_stage,
        sector_relevance=record.sector_relevance,
        thesis=record.thesis,
        check_fit_notes=record.check_fit_notes,
        warm_intro_path=record.warm_intro_path,
        risk_flags=record.risk_flags,
        pipeline_stage=record.pipeline_stage,
        last_contact_at=record.last_contact_at.isoformat() if record.last_contact_at else None,
        next_follow_up_at=record.next_follow_up_at.isoformat() if record.next_follow_up_at else None,
    )


@router.delete("/{investor_id}", response_model=DeleteResponse)
def delete_investor(investor_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> DeleteResponse:
    record = db.query(Investor).filter(Investor.id == investor_id, Investor.workspace_id == workspace.id).one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Investor not found")
    if record.person_id:
        db.query(Person).filter(Person.id == record.person_id).delete()
    db.delete(record)
    db.commit()
    return DeleteResponse(status="deleted")
