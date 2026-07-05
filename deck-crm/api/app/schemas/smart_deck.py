from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.deck_workflow import WorkflowJobStatus, WorkflowJobType, WorkflowNextAction, WorkflowPhase


ALLOWED_RENDER_TOKENS = {
    "brand.surface",
    "brand.surfaceAlt",
    "brand.heading",
    "brand.body",
    "brand.accent",
    "brand.muted",
}
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


def _validate_token_or_hex(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if value in ALLOWED_RENDER_TOKENS or HEX_COLOR_PATTERN.match(value):
        return value
    raise ValueError(f"{field_name} must be an approved brand token or 6-digit hex color.")


def _validate_internal_asset_url(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith(("/api/", "/uploads/", "/static/")):
        return value
    raise ValueError("assetUrl must be an internal asset URL.")


class RenderSchemaStyle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fill: str | None = None
    opacity: float | None = Field(default=None, ge=0, le=1)
    radius: int | None = Field(default=None, ge=0, le=999)

    @field_validator("fill")
    @classmethod
    def validate_fill(cls, value: str | None) -> str | None:
        return _validate_token_or_hex(value, "fill")


class RenderSchemaBackgroundLayer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: Literal["shape", "image"]
    shape: Literal["rectangle", "circle", "line"] | None = None
    role: str | None = None
    x: int = Field(ge=-3840, le=3840)
    y: int = Field(ge=-2160, le=2160)
    width: int = Field(gt=0, le=3840)
    height: int = Field(gt=0, le=2160)
    zIndex: int = Field(default=0, ge=-10, le=10)
    style: RenderSchemaStyle = Field(default_factory=RenderSchemaStyle)
    assetUrl: str | None = None

    @field_validator("assetUrl")
    @classmethod
    def validate_asset_url(cls, value: str | None) -> str | None:
        return _validate_internal_asset_url(value)

    @model_validator(mode="after")
    def validate_layer(self) -> "RenderSchemaBackgroundLayer":
        if self.type == "shape" and self.shape is None:
            raise ValueError(f"Background layer {self.id} requires shape.")
        if self.type == "image" and not self.assetUrl:
            raise ValueError(f"Background image layer {self.id} requires assetUrl.")
        return self


class RenderSchemaBackground(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["token", "color", "gradient", "image", "layered"]
    value: str | None = None
    fill: str | None = None
    layers: list[RenderSchemaBackgroundLayer] = Field(default_factory=list, max_length=12)

    @field_validator("value", "fill")
    @classmethod
    def validate_background_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value.startswith("linear-gradient("):
            for token in re.findall(r"brand\.[A-Za-z0-9]+", value):
                if token not in ALLOWED_RENDER_TOKENS:
                    raise ValueError(f"Unsupported gradient token: {token}")
            return value
        return _validate_token_or_hex(value, "background")

    @model_validator(mode="after")
    def validate_background(self) -> "RenderSchemaBackground":
        if self.type == "layered":
            if not self.fill:
                raise ValueError("Layered background requires fill.")
            return self
        if not self.value:
            raise ValueError(f"Background type {self.type} requires value.")
        if self.type == "image":
            _validate_internal_asset_url(self.value)
        return self


class RenderSchemaElement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: Literal["text", "shape", "image", "chart_placeholder"]
    text: str | None = Field(default=None, max_length=1000)
    x: int = Field(ge=0, le=1920)
    y: int = Field(ge=0, le=1080)
    width: int = Field(gt=0, le=1920)
    height: int = Field(gt=0, le=1080)
    zIndex: int = Field(default=20, ge=0, le=100)
    fontSize: int | None = Field(default=None, ge=8, le=160)
    fontWeight: str | None = None
    colorToken: str | None = None
    fillToken: str | None = None
    assetUrl: str | None = None
    analyticsKey: str | None = Field(default=None, max_length=80)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if "<" in value or ">" in value or "script" in lowered or "javascript:" in lowered:
            raise ValueError("text must not contain raw HTML or script-like content.")
        return value

    @field_validator("colorToken", "fillToken")
    @classmethod
    def validate_token(cls, value: str | None) -> str | None:
        return _validate_token_or_hex(value, "token")

    @field_validator("assetUrl")
    @classmethod
    def validate_asset_url(cls, value: str | None) -> str | None:
        return _validate_internal_asset_url(value)


class RenderSchemaAnalytics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slidePurpose: str | None = Field(default=None, max_length=80)
    audience: str | None = Field(default=None, max_length=120)
    sourceFactIds: list[str] = Field(default_factory=list, max_length=16)
    sourceFactsUsed: list[str] = Field(default_factory=list, max_length=16)
    assumptions: list[str] = Field(default_factory=list, max_length=12)
    missingInputs: list[str] = Field(default_factory=list, max_length=12)
    qualityWarnings: list[str] = Field(default_factory=list, max_length=12)
    confidence: float | None = Field(default=None, ge=0, le=1)
    trackedEvents: list[Literal["slide_view", "slide_time_spent", "cta_click", "element_click", "element_hover"]] = Field(
        default_factory=list,
        max_length=8,
    )


class RenderSchemaExportMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exportReady: bool = True
    renderer: Literal["smart_deck_scene_graph"] = "smart_deck_scene_graph"
    supportedFormats: list[Literal["digital", "pdf", "pptx", "preview_image"]] = Field(
        default_factory=lambda: ["digital", "preview_image"],
        max_length=4,
    )


class RenderSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: Literal["smart-deck-render-schema.v1"] = "smart-deck-render-schema.v1"
    width: int = Field(default=1920, ge=320, le=3840)
    height: int = Field(default=1080, ge=240, le=2160)
    background: RenderSchemaBackground
    elements: list[RenderSchemaElement] = Field(min_length=1, max_length=32)
    brandTokensUsed: list[str] = Field(default_factory=list, max_length=24)
    analytics: RenderSchemaAnalytics = Field(default_factory=RenderSchemaAnalytics)
    exportMetadata: RenderSchemaExportMetadata = Field(default_factory=RenderSchemaExportMetadata)

    @field_validator("brandTokensUsed")
    @classmethod
    def validate_brand_tokens_used(cls, value: list[str]) -> list[str]:
        unsupported = [token for token in value if token not in ALLOWED_RENDER_TOKENS]
        if unsupported:
            raise ValueError(f"Unsupported brandTokensUsed values: {', '.join(unsupported)}")
        return value

    @model_validator(mode="after")
    def validate_element_bounds(self) -> "RenderSchema":
        for element in self.elements:
            if element.x + element.width > self.width or element.y + element.height > self.height:
                raise ValueError(f"Element {element.id} extends outside the slide canvas.")
            if element.type == "text" and not (element.text or "").strip():
                raise ValueError(f"Text element {element.id} requires text.")
            if element.type == "image" and not element.assetUrl:
                raise ValueError(f"Image element {element.id} requires assetUrl.")
        return self


class SourceSlideResponse(BaseModel):
    id: str
    deckId: str
    slideNumber: int
    title: str
    extractedText: str
    thumbnailUrl: str | None = None
    previewImageUrl: str | None = None
    layoutHints: dict = Field(default_factory=dict)
    blocks: list[dict] = Field(default_factory=list)


class GenerationJobResponse(BaseModel):
    id: str
    deckId: str
    status: str
    provider: str
    model: str | None = None
    prompt: str
    selectedSourceSlideIds: list[str]
    styleId: str | None = None
    brandProductId: str | None = None
    errorMessage: str | None = None
    createdAt: str
    updatedAt: str
    completedAt: str | None = None


class GeneratedSlideCodeVersionResponse(BaseModel):
    id: str
    generatedSlideId: str
    versionNumber: int
    codeKind: str
    schemaVersion: str
    renderSchema: RenderSchema
    codeJson: dict | None = None
    bucketRenderSchemaKey: str | None = None
    bucketCodeKey: str | None = None
    bucketThumbnailKey: str | None = None
    status: str
    validationErrors: list[dict] | None = None
    createdAt: str


class GeneratedSlideElementVersionResponse(BaseModel):
    id: str
    elementId: str
    generatedSlideId: str
    designVersionId: str
    versionNumber: int
    source: str
    status: str
    style: dict | None = None
    content: dict | None = None
    changeSummary: str | None = None
    createdAt: str


class GeneratedSlideElementResponse(BaseModel):
    id: str
    generatedSlideId: str
    deckId: str
    designVersionId: str
    sourceSlideId: str | None = None
    elementKey: str
    elementType: str
    parentElementId: str | None = None
    zIndex: int
    x: int
    y: int
    width: int
    height: int
    rotation: float
    locked: bool
    visible: bool
    style: dict | None = None
    content: dict | None = None
    versions: list[GeneratedSlideElementVersionResponse] = Field(default_factory=list)
    createdAt: str
    updatedAt: str


class GeneratedSlideResponse(BaseModel):
    id: str
    deckId: str
    designVersionId: str
    generationJobId: str | None = None
    sourceSlideId: str | None = None
    slideNumber: int
    title: str
    status: str
    renderSchema: RenderSchema
    designTokens: dict | None = None
    previewImageUrl: str | None = None
    validationStatus: str
    elements: list[GeneratedSlideElementResponse] = Field(default_factory=list)
    createdAt: str
    updatedAt: str
    generated_slide_id: str | None = None
    slide_index: int | None = None
    archetype_id: str | None = None
    current_version_id: str | None = None
    current_design_version_id: str | None = None
    version_number: int | None = None
    render_schema_json: dict | None = None
    bucket_render_schema_key: str | None = None
    bucket_artifacts: dict | None = None


class DesignVersionResponse(BaseModel):
    id: str
    deckId: str
    generationJobId: str | None = None
    name: str
    status: str
    isActive: bool
    summary: str | None = None
    generatedSlides: list[GeneratedSlideResponse] = Field(default_factory=list)
    createdAt: str
    updatedAt: str
    appliedAt: str | None = None
    discardedAt: str | None = None
    state: str | None = None
    source: str | None = None
    changed_slide_ids: list[str] = Field(default_factory=list)
    created_at: str | None = None


class SmartDeckWorkspaceStateResponse(BaseModel):
    id: str
    deckId: str
    userId: str | None = None
    activeDesignVersionId: str | None = None
    activeSourceSlideId: str | None = None
    activeGeneratedSlideId: str | None = None
    selectedElementId: str | None = None
    status: str
    createdAt: str
    updatedAt: str


class SmartDeckPreferenceResponse(BaseModel):
    id: str
    workspaceId: str
    deckId: str
    userId: str | None = None
    selectedSourceSlideIds: list[str] = Field(default_factory=list)
    activeSourceSlideId: str | None = None
    activeDesignVersionId: str | None = None
    activeGeneratedSlideId: str | None = None
    selectedElementId: str | None = None
    audience: str | None = None
    deckType: str | None = None
    preferredModel: str | None = None
    selectedSubject: str | None = None
    selectedActionId: str | None = None
    zoomLevel: float = 1.0
    canvasFitMode: Literal["fit", "fill", "actual_size"] = "fit"
    rightPanelOpen: bool = True
    slideRailOpen: bool = True
    updatedAt: str


class SmartDeckMessageResponse(BaseModel):
    id: str
    workspaceId: str
    deckId: str
    generationJobId: str | None = None
    role: Literal["user", "assistant", "system"]
    content: str
    selectedSourceSlideIds: list[str] = Field(default_factory=list)
    metadata: dict | None = None
    createdAt: str


class GeneratedSlideCodeArtifactsResponse(BaseModel):
    render_schema_url: str | None = None
    code_url: str | None = None
    thumbnail_url: str | None = None


class GeneratedSlideThumbnailResponse(BaseModel):
    generated_slide_id: str
    code_version_id: str
    bucket_thumbnail_key: str
    thumbnail_url: str | None = None


class DesignTokenResponse(BaseModel):
    id: str
    deckId: str
    designVersionId: str | None = None
    generatedSlideId: str | None = None
    tokenName: str
    tokenValue: str
    tokenType: str
    source: str
    createdAt: str
    updatedAt: str


class SmartDeckWorkspaceResponse(BaseModel):
    deck: dict
    workspace: SmartDeckWorkspaceStateResponse
    preferences: SmartDeckPreferenceResponse
    messages: list[SmartDeckMessageResponse] = Field(default_factory=list)
    designTokens: list[DesignTokenResponse] = Field(default_factory=list)
    sourceSlides: list[SourceSlideResponse]
    generationJobs: list[GenerationJobResponse]
    designVersions: list[DesignVersionResponse]
    activeDesignVersionId: str | None = None
    activeSourceSlideId: str | None = None
    activeGeneratedSlideId: str | None = None
    generatedSlides: list[GeneratedSlideResponse]
    deck_id: str | None = None
    current_design_version_id: str | None = None
    current_batch_id: str | None = None
    slides: list[dict] = Field(default_factory=list)
    design_versions: list[dict] = Field(default_factory=list)
    knowledgeMetadata: dict = Field(default_factory=dict)
    runtimeContext: dict = Field(default_factory=dict)
    runtimeCapabilities: dict = Field(default_factory=dict)


class CreateSmartDeckGenerationJobInput(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    selectedSourceSlideIds: list[str] = Field(min_length=1, max_length=20)
    styleId: str | None = Field(default=None, max_length=120)
    brandProductId: str | None = Field(default="deck-aistack-codes", max_length=120)
    additionalContext: str | None = Field(default=None, max_length=4000)
    deckType: str | None = Field(default=None, max_length=40)
    audience: str | None = Field(default=None, max_length=120)
    preferredModel: str | None = Field(default=None, max_length=120)
    selectedElementId: str | None = Field(default=None, max_length=120)
    selectedSubject: str | None = Field(default=None, max_length=80)
    actionId: str | None = Field(default=None, max_length=120)
    actionPrompt: str | None = Field(default=None, max_length=4000)
    userPrompt: str | None = Field(default=None, max_length=4000)
    latestBatchId: str | None = Field(default=None, max_length=120)
    detectedSubjects: list[dict] | None = None
    subjectConfidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_unique_selected_slides(self) -> "CreateSmartDeckGenerationJobInput":
        if len(set(self.selectedSourceSlideIds)) != len(self.selectedSourceSlideIds):
            raise ValueError("selectedSourceSlideIds must not contain duplicates.")
        return self


class CreateSmartDeckGenerationJobResponse(BaseModel):
    generationJob: GenerationJobResponse
    designVersion: DesignVersionResponse | None = None
    workspace: SmartDeckWorkspaceResponse | None = None


class UpdateSmartDeckPreferenceInput(BaseModel):
    selectedSourceSlideIds: list[str] | None = Field(default=None, max_length=20)
    activeSourceSlideId: str | None = None
    activeDesignVersionId: str | None = None
    activeGeneratedSlideId: str | None = None
    selectedElementId: str | None = None
    audience: str | None = Field(default=None, max_length=120)
    deckType: str | None = Field(default=None, max_length=40)
    preferredModel: str | None = Field(default=None, max_length=120)
    selectedSubject: str | None = Field(default=None, max_length=80)
    selectedActionId: str | None = Field(default=None, max_length=120)
    zoomLevel: float | None = Field(default=None, ge=0.1, le=5.0)
    canvasFitMode: Literal["fit", "fill", "actual_size"] | None = None
    rightPanelOpen: bool | None = None
    slideRailOpen: bool | None = None

    @model_validator(mode="after")
    def validate_unique_selected_slides(self) -> "UpdateSmartDeckPreferenceInput":
        if self.selectedSourceSlideIds is not None and len(set(self.selectedSourceSlideIds)) != len(self.selectedSourceSlideIds):
            raise ValueError("selectedSourceSlideIds must not contain duplicates.")
        return self


class CreateSmartDeckMessageInput(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=4000)
    generationJobId: str | None = None
    selectedSourceSlideIds: list[str] = Field(default_factory=list, max_length=20)
    metadata: dict | None = None

    @model_validator(mode="after")
    def validate_unique_selected_slides(self) -> "CreateSmartDeckMessageInput":
        if len(set(self.selectedSourceSlideIds)) != len(self.selectedSourceSlideIds):
            raise ValueError("selectedSourceSlideIds must not contain duplicates.")
        return self


class SmartDeckMessagesRouteResponse(BaseModel):
    messages: list[SmartDeckMessageResponse]


AssistantIntentType = Literal[
    "market_size",
    "market_research",
    "financial_projection",
    "competitor_landscape",
    "customer_persona",
    "investor_objections",
    "narrative_flow",
    "slide_critique",
    "due_diligence_risks",
    "missing_evidence",
    "rewrite_for_vc",
    "create_design_version",
]

AssistantScope = Literal["current_slide", "selected_slides", "whole_deck"]


class CreateSmartDeckAssistantRunInput(BaseModel):
    intentType: AssistantIntentType
    scope: AssistantScope = "current_slide"
    instruction: str = Field(min_length=1, max_length=4000)
    selectedSourceSlideIds: list[str] = Field(default_factory=list, max_length=20)
    activeSourceSlideId: str | None = None
    audience: str | None = Field(default=None, max_length=120)
    saveInsight: bool = True

    @model_validator(mode="after")
    def validate_unique_selected_slides(self) -> "CreateSmartDeckAssistantRunInput":
        if len(set(self.selectedSourceSlideIds)) != len(self.selectedSourceSlideIds):
            raise ValueError("selectedSourceSlideIds must not contain duplicates.")
        if self.scope == "selected_slides" and not self.selectedSourceSlideIds:
            raise ValueError("selectedSourceSlideIds is required when scope is selected_slides.")
        return self


class SmartDeckAssistantInsightResponse(BaseModel):
    title: str
    summary: str
    content: dict = Field(default_factory=dict)
    confidence: Literal["low", "medium", "high"] = "medium"
    assumptions: list[str] = Field(default_factory=list)
    missingEvidence: list[str] = Field(default_factory=list)
    suggestedSlideUpdate: str | None = None
    recommendedAction: Literal["save_insight", "add_to_slide", "create_version", "none"] = "save_insight"


class SmartDeckAssistantRunResponse(BaseModel):
    runId: str
    deckId: str
    intentType: AssistantIntentType
    scope: AssistantScope
    status: Literal["queued", "running", "completed", "failed"] = "completed"
    outputType: Literal["insight", "design_version", "critique", "research"] = "insight"
    provider: str
    model: str | None = None
    inputContext: dict
    insight: SmartDeckAssistantInsightResponse
    assistantMessage: SmartDeckMessageResponse
    savedArtifactId: str | None = None


class DesignTokensRouteResponse(BaseModel):
    designTokens: list[DesignTokenResponse]


class DesignVersionsRouteResponse(BaseModel):
    designVersions: list[DesignVersionResponse]
    activeDesignVersionId: str | None = None
    workflowId: str | None = None
    workflowPhase: WorkflowPhase | None = None
    workflowStatus: WorkflowJobStatus | None = None
    workflowJobId: str | None = None
    workflowJobType: WorkflowJobType | None = None
    workflowJobStatus: WorkflowJobStatus | None = None
    nextAction: WorkflowNextAction | None = None


class GeneratedSlideCodeRouteResponse(BaseModel):
    generatedSlide: GeneratedSlideResponse
    codeVersion: GeneratedSlideCodeVersionResponse


class GeneratedSlideSceneGraphResponse(BaseModel):
    generatedSlide: GeneratedSlideResponse
    elements: list[GeneratedSlideElementResponse]
    activeElementVersions: list[GeneratedSlideElementVersionResponse]


class UpdateSmartDeckSelectionInput(BaseModel):
    activeSourceSlideId: str | None = None
    activeGeneratedSlideId: str | None = None
    selectedElementId: str | None = None


class ElementVariationJobResponse(BaseModel):
    id: str
    deckId: str
    workspaceId: str
    generatedSlideId: str
    elementId: str
    baseElementVersionId: str | None = None
    instruction: str
    variationCount: int
    status: str
    outputElementVersionId: str | None = None
    errorMessage: str | None = None
    createdAt: str
    startedAt: str | None = None
    completedAt: str | None = None


class CreateElementVariationJobInput(BaseModel):
    instruction: str = Field(min_length=1, max_length=2000)
    variationCount: int = Field(default=1, ge=1, le=3)


class CreateElementVariationJobResponse(BaseModel):
    variationJob: ElementVariationJobResponse
    element: GeneratedSlideElementResponse
    outputVersion: GeneratedSlideElementVersionResponse
    generatedSlide: GeneratedSlideResponse | None = None
    designVersion: DesignVersionResponse | None = None
    workspace: SmartDeckWorkspaceResponse | None = None


class ApplyElementVersionResponse(BaseModel):
    element: GeneratedSlideElementResponse
    appliedVersion: GeneratedSlideElementVersionResponse
    generatedSlide: GeneratedSlideResponse
