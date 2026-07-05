from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.db.models import Contact, Person
from app.schemas.crm import ContactCreate, ContactResponse, DeleteResponse

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactResponse])
def list_contacts(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[ContactResponse]:
    records = db.query(Contact).filter(Contact.workspace_id == workspace.id).order_by(Contact.created_at.desc()).all()
    return [
        ContactResponse(
            id=item.id,
            person_id=item.person_id,
            name=item.name,
            email=item.email,
            company=item.company,
            role=item.role,
            contact_type=item.contact_type,
            relationship_status=item.relationship_status,
            notes=item.notes,
            last_contact_at=item.last_contact_at.isoformat() if item.last_contact_at else None,
            next_follow_up_at=item.next_follow_up_at.isoformat() if item.next_follow_up_at else None,
        )
        for item in records
    ]


@router.post("", response_model=ContactResponse)
def create_contact(
    payload: ContactCreate,
    workspace=Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> ContactResponse:
    person = Person(workspace_id=workspace.id, name=payload.name, email=payload.email,
                    company=payload.company, role=payload.role,
                    relationship_status=payload.relationship_status, notes=payload.notes,
                    source_kind="contact")
    db.add(person)
    db.flush()
    record = Contact(workspace_id=workspace.id, person_id=person.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return ContactResponse(
        id=record.id,
        person_id=record.person_id,
        name=record.name,
        email=record.email,
        company=record.company,
        role=record.role,
        contact_type=record.contact_type,
        relationship_status=record.relationship_status,
        notes=record.notes,
        last_contact_at=None,
        next_follow_up_at=None,
    )


@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: str, payload: ContactCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> ContactResponse:
    record = db.query(Contact).filter(Contact.id == contact_id, Contact.workspace_id == workspace.id).one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    for field, value in payload.model_dump().items():
        setattr(record, field, value)
    if record.person_id:
        person = db.query(Person).filter(Person.id == record.person_id).one_or_none()
        if person:
            for field in ("name", "email", "company", "role", "relationship_status", "notes"):
                setattr(person, field, getattr(record, field))
    db.commit()
    db.refresh(record)
    return ContactResponse(
        id=record.id,
        person_id=record.person_id,
        name=record.name,
        email=record.email,
        company=record.company,
        role=record.role,
        contact_type=record.contact_type,
        relationship_status=record.relationship_status,
        notes=record.notes,
        last_contact_at=record.last_contact_at.isoformat() if record.last_contact_at else None,
        next_follow_up_at=record.next_follow_up_at.isoformat() if record.next_follow_up_at else None,
    )


@router.delete("/{contact_id}", response_model=DeleteResponse)
def delete_contact(contact_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> DeleteResponse:
    record = db.query(Contact).filter(Contact.id == contact_id, Contact.workspace_id == workspace.id).one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    if record.person_id:
        db.query(Person).filter(Person.id == record.person_id).delete()
    db.delete(record)
    db.commit()
    return DeleteResponse(status="deleted")
