from pydantic import BaseModel


class AudienceProfileResponse(BaseModel):
    id: str
    code: str
    label: str
    description: str


class DeckSlideResponse(BaseModel):
    id: str
    slide_order: int
    title: str
    content: str


class DeckResponse(BaseModel):
    id: str
    title: str
    audience: str | None = None
    status: str
    source_file_name: str | None = None
    slides: list[DeckSlideResponse]


class DeckArtifactResponse(BaseModel):
    id: str
    deck_id: str
    generation_run_id: str
    artifact_type: str
    artifact_status: str
    title: str
    content_markdown: str
    export_enabled: bool
    created_at: str


class DeckGenerationRequest(BaseModel):
    audience_code: str
    instruction: str
    api_key: str | None = None
    provider: str | None = None


class DeckGenerationResponse(BaseModel):
    run_id: str
    artifact: DeckArtifactResponse


class DeckGenerationRunResponse(BaseModel):
    id: str
    deck_id: str
    deck_title: str | None = None
    audience_profile_id: str | None = None
    audience_label: str | None = None
    provider: str
    model: str
    status: str
    prompt_summary: str
    created_at: str
    artifacts: list[DeckArtifactResponse] = []
    telemetry_event_count: int = 0


class DeckArtifactDetailResponse(DeckArtifactResponse):
    deck_title: str | None = None
    audience_label: str | None = None
    run: DeckGenerationRunResponse | None = None
