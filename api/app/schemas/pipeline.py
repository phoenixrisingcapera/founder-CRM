from pydantic import BaseModel


class PipelineDealCreate(BaseModel):
    name: str
    stage: str
    status: str = "active"
    target_raise_amount: str | None = None
    notes: str | None = None
    person_id: str | None = None


class PipelineDealResponse(PipelineDealCreate):
    id: str
    person_name: str | None = None


class InteractionNoteCreate(BaseModel):
    title: str
    body: str
    person_id: str | None = None


class InteractionNoteResponse(InteractionNoteCreate):
    id: str
    created_at: str


class FollowUpTaskCreate(BaseModel):
    title: str
    status: str = "open"
    due_at: str | None = None
    person_id: str | None = None


class FollowUpTaskResponse(FollowUpTaskCreate):
    id: str
