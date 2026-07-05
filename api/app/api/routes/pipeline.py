from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace, get_db
from app.db.models import FollowUpTask, InteractionNote, Person, PipelineDeal
from app.schemas.crm import DeleteResponse
from app.schemas.pipeline import (
    FollowUpTaskCreate,
    FollowUpTaskResponse,
    InteractionNoteCreate,
    InteractionNoteResponse,
    PipelineDealCreate,
    PipelineDealResponse,
)

router = APIRouter(tags=["pipeline"])


@router.get("/pipeline-deals", response_model=list[PipelineDealResponse])
def list_pipeline_deals(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[PipelineDealResponse]:
    rows = db.query(PipelineDeal).filter(PipelineDeal.workspace_id == workspace.id).order_by(PipelineDeal.created_at.desc()).all()
    result = []
    for row in rows:
        person_name = None
        if row.person_id:
            person = db.query(Person).filter(Person.id == row.person_id).first()
            if person:
                person_name = person.name
        result.append(
            PipelineDealResponse(id=row.id, name=row.name, stage=row.stage, status=row.status,
                                 target_raise_amount=row.target_raise_amount, notes=row.notes,
                                 person_id=row.person_id, person_name=person_name)
        )
    return result


@router.post("/pipeline-deals", response_model=PipelineDealResponse)
def create_pipeline_deal(payload: PipelineDealCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> PipelineDealResponse:
    row = PipelineDeal(workspace_id=workspace.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    person_name = None
    if row.person_id:
        person = db.query(Person).filter(Person.id == row.person_id).first()
        if person:
            person_name = person.name
    return PipelineDealResponse(id=row.id, name=row.name, stage=row.stage, status=row.status,
                                target_raise_amount=row.target_raise_amount, notes=row.notes,
                                person_id=row.person_id, person_name=person_name)


@router.put("/pipeline-deals/{deal_id}", response_model=PipelineDealResponse)
def update_pipeline_deal(deal_id: str, payload: PipelineDealCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> PipelineDealResponse:
    row = db.query(PipelineDeal).filter(PipelineDeal.id == deal_id, PipelineDeal.workspace_id == workspace.id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Pipeline deal not found")
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    person_name = None
    if row.person_id:
        person = db.query(Person).filter(Person.id == row.person_id).first()
        if person:
            person_name = person.name
    return PipelineDealResponse(id=row.id, name=row.name, stage=row.stage, status=row.status,
                                target_raise_amount=row.target_raise_amount, notes=row.notes,
                                person_id=row.person_id, person_name=person_name)


@router.delete("/pipeline-deals/{deal_id}", response_model=DeleteResponse)
def delete_pipeline_deal(deal_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> DeleteResponse:
    row = db.query(PipelineDeal).filter(PipelineDeal.id == deal_id, PipelineDeal.workspace_id == workspace.id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Pipeline deal not found")
    db.delete(row)
    db.commit()
    return DeleteResponse(status="deleted")


@router.get("/notes", response_model=list[InteractionNoteResponse])
def list_notes(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[InteractionNoteResponse]:
    rows = db.query(InteractionNote).filter(InteractionNote.workspace_id == workspace.id).order_by(InteractionNote.created_at.desc()).all()
    return [InteractionNoteResponse(id=row.id, title=row.title, body=row.body, person_id=row.person_id, created_at=row.created_at.isoformat()) for row in rows]


@router.post("/notes", response_model=InteractionNoteResponse)
def create_note(payload: InteractionNoteCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> InteractionNoteResponse:
    row = InteractionNote(workspace_id=workspace.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return InteractionNoteResponse(id=row.id, title=row.title, body=row.body, person_id=row.person_id, created_at=row.created_at.isoformat())


@router.put("/notes/{note_id}", response_model=InteractionNoteResponse)
def update_note(note_id: str, payload: InteractionNoteCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> InteractionNoteResponse:
    row = db.query(InteractionNote).filter(InteractionNote.id == note_id, InteractionNote.workspace_id == workspace.id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return InteractionNoteResponse(id=row.id, title=row.title, body=row.body, person_id=row.person_id, created_at=row.created_at.isoformat())


@router.delete("/notes/{note_id}", response_model=DeleteResponse)
def delete_note(note_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> DeleteResponse:
    row = db.query(InteractionNote).filter(InteractionNote.id == note_id, InteractionNote.workspace_id == workspace.id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(row)
    db.commit()
    return DeleteResponse(status="deleted")


@router.get("/tasks", response_model=list[FollowUpTaskResponse])
def list_tasks(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[FollowUpTaskResponse]:
    rows = db.query(FollowUpTask).filter(FollowUpTask.workspace_id == workspace.id).order_by(FollowUpTask.created_at.desc()).all()
    return [FollowUpTaskResponse(id=row.id, title=row.title, status=row.status, due_at=row.due_at.isoformat() if row.due_at else None, person_id=row.person_id) for row in rows]


@router.post("/tasks", response_model=FollowUpTaskResponse)
def create_task(payload: FollowUpTaskCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> FollowUpTaskResponse:
    due_at = datetime.fromisoformat(payload.due_at) if payload.due_at else None
    row = FollowUpTask(
        workspace_id=workspace.id,
        title=payload.title,
        status=payload.status,
        due_at=due_at,
        person_id=payload.person_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return FollowUpTaskResponse(id=row.id, title=row.title, status=row.status, due_at=row.due_at.isoformat() if row.due_at else None, person_id=row.person_id)


@router.put("/tasks/{task_id}", response_model=FollowUpTaskResponse)
def update_task(task_id: str, payload: FollowUpTaskCreate, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> FollowUpTaskResponse:
    row = db.query(FollowUpTask).filter(FollowUpTask.id == task_id, FollowUpTask.workspace_id == workspace.id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    row.title = payload.title
    row.status = payload.status
    row.due_at = datetime.fromisoformat(payload.due_at) if payload.due_at else None
    row.person_id = payload.person_id
    db.commit()
    db.refresh(row)
    return FollowUpTaskResponse(id=row.id, title=row.title, status=row.status, due_at=row.due_at.isoformat() if row.due_at else None, person_id=row.person_id)


@router.delete("/tasks/{task_id}", response_model=DeleteResponse)
def delete_task(task_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> DeleteResponse:
    row = db.query(FollowUpTask).filter(FollowUpTask.id == task_id, FollowUpTask.workspace_id == workspace.id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(row)
    db.commit()
    return DeleteResponse(status="deleted")
