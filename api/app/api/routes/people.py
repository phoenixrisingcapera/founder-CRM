from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.db.models import Contact, Investor, Person
from app.schemas.crm import DeleteResponse, PersonCreate, PersonResponse

router = APIRouter(prefix="/people", tags=["people"])


@router.get("", response_model=list[PersonResponse])
def list_people(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[PersonResponse]:
    records = db.query(Person).filter(Person.workspace_id == workspace.id).order_by(Person.created_at.desc()).all()
    return [
        PersonResponse(
            id=item.id,
            name=item.name,
            email=item.email,
            company=item.company,
            role=item.role,
            relationship_status=item.relationship_status,
            notes=item.notes,
            source_kind=item.source_kind,
            last_contact_at=item.last_contact_at.isoformat() if item.last_contact_at else None,
            next_follow_up_at=item.next_follow_up_at.isoformat() if item.next_follow_up_at else None,
            created_at=item.created_at.isoformat() if item.created_at else None,
        )
        for item in records
    ]


@router.post("", response_model=PersonResponse)
def create_person(
    payload: PersonCreate,
    workspace=Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> PersonResponse:
    record = Person(workspace_id=workspace.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return PersonResponse(
        id=record.id,
        name=record.name,
        email=record.email,
        company=record.company,
        role=record.role,
        relationship_status=record.relationship_status,
        notes=record.notes,
        source_kind=record.source_kind,
        last_contact_at=None,
        next_follow_up_at=None,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(person_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> PersonResponse:
    record = db.query(Person).filter(Person.id == person_id, Person.workspace_id == workspace.id).one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return PersonResponse(
        id=record.id,
        name=record.name,
        email=record.email,
        company=record.company,
        role=record.role,
        relationship_status=record.relationship_status,
        notes=record.notes,
        source_kind=record.source_kind,
        last_contact_at=record.last_contact_at.isoformat() if record.last_contact_at else None,
        next_follow_up_at=record.next_follow_up_at.isoformat() if record.next_follow_up_at else None,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


@router.put("/{person_id}", response_model=PersonResponse)
def update_person(person_id: str, payload: PersonCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> PersonResponse:
    record = db.query(Person).filter(Person.id == person_id, Person.workspace_id == workspace.id).one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Person not found")
    for field, value in payload.model_dump().items():
        setattr(record, field, value)
    contact = db.query(Contact).filter(Contact.person_id == record.id).first()
    if contact:
        for field in ("name", "email", "company", "role", "relationship_status", "notes"):
            setattr(contact, field, getattr(record, field))
    db.commit()
    db.refresh(record)
    return PersonResponse(
        id=record.id,
        name=record.name,
        email=record.email,
        company=record.company,
        role=record.role,
        relationship_status=record.relationship_status,
        notes=record.notes,
        source_kind=record.source_kind,
        last_contact_at=record.last_contact_at.isoformat() if record.last_contact_at else None,
        next_follow_up_at=record.next_follow_up_at.isoformat() if record.next_follow_up_at else None,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


@router.delete("/{person_id}", response_model=DeleteResponse)
def delete_person(person_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> DeleteResponse:
    record = db.query(Person).filter(Person.id == person_id, Person.workspace_id == workspace.id).one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Person not found")
    db.query(Contact).filter(Contact.person_id == record.id).delete()
    db.query(Investor).filter(Investor.person_id == record.id).delete()
    db.delete(record)
    db.commit()
    return DeleteResponse(status="deleted")
