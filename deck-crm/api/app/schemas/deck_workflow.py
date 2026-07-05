from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


WorkflowJobType = Literal[
    "source_ingestion",
    "source_extraction",
    "miniatures",
    "brand_extraction",
    "smart_deck_context",
    "db_publisher",
    "llm_generation",
    "llm_parallelization",
    "schema_validation",
    "preview_render",
    "apply_version",
    "export",
]

WorkflowJobStatus = Literal[
    "queued",
    "running",
    "completed",
    "failed_retryable",
    "failed_final",
    "blocked",
    "timed_out",
]

WorkflowPhase = Literal[
    "upload_accepted",
    "source_file_saved",
    "source_ingestion_queued",
    "source_ingestion_running",
    "source_extraction_queued",
    "source_extraction_running",
    "miniatures_queued",
    "miniatures_running",
    "brand_extraction_queued",
    "brand_extraction_running",
    "smart_deck_context_queued",
    "smart_deck_context_running",
    "source_ready",
    "generation_queued",
    "generation_running",
    "llm_parallelization_queued",
    "llm_parallelization_running",
    "llm_parallelization_ready",
    "schema_validation_queued",
    "schema_validation_running",
    "preview_render_queued",
    "preview_render_running",
    "preview_ready",
    "apply_queued",
    "apply_running",
    "applied",
    "export_queued",
    "export_running",
    "export_ready",
    "smart_deck_ready",
    "failed_retryable",
    "failed_final",
    "needs_manual_review",
]

WorkflowNextAction = Literal[
    "continue_upload",
    "view_processing",
    "apply_preview",
    "open_smart_deck",
    "configure_provider",
    "retry_job",
    "manual_review",
    "create_smart_deck",
]

WorkflowBlockingReason = Literal[
    "provider_not_configured",
    "dependency_failed",
    "worker_timeout",
    "worker_lease_expired",
    "worker_heartbeat_expired",
    "smart_deck_not_ready",
    "preview_not_ready",
    "export_not_ready",
    "idempotency_key_conflict",
    "source_extraction_failed",
    "thumbnail_generation_failed",
    "brand_extraction_failed",
    "smart_deck_context_failed",
    "llm_generation_failed",
    "llm_parallelization_failed",
    "schema_validation_failed",
    "preview_render_failed",
    "apply_version_failed",
    "export_failed",
]

WorkflowPublishedPhase = Literal[
    "smart_deck_ready",
    "preview_ready",
    "applied",
    "export_ready",
]


class WorkflowJobErrorResponse(BaseModel):
    code: str
    message: str
    recoverable: bool
    nextAction: WorkflowNextAction | None = None


class WorkflowJobEventResponse(BaseModel):
    eventType: str
    fromStatus: str | None = None
    toStatus: str
    message: str | None = None
    createdAt: str


class WorkflowJobArtifactResponse(BaseModel):
    artifactType: str
    artifactId: str | None = None
    storageKey: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowJobSummaryResponse(BaseModel):
    jobId: str
    jobType: WorkflowJobType
    status: WorkflowJobStatus
    phase: WorkflowPhase
    attemptCount: int | None = None
    maxAttempts: int | None = None
    recoveryCount: int | None = None
    progress: int | None = None
    queuedAt: str | None = None
    startedAt: str | None = None
    heartbeatAt: str | None = None
    updatedAt: str | None = None
    lockedUntil: str | None = None
    lastRecoveredAt: str | None = None
    lastRecoveredBy: str | None = None
    completedAt: str | None = None
    failedAt: str | None = None
    publishedPhase: WorkflowPublishedPhase | None = None
    publishedAt: str | None = None
    workerId: str | None = None
    terminal: bool = False
    terminalReason: str | None = None
    retryEligible: bool = False
    error: WorkflowJobErrorResponse | None = None


class WorkflowSourceEnrichmentResponse(BaseModel):
    source: str | None = None
    llmStatus: str | None = None
    provider: str | None = None
    model: str | None = None
    message: str | None = None
    badge: str | None = None


class WorkflowSourceBlockResponse(BaseModel):
    blockIndex: int
    rawText: str
    normalizedText: str
    blockType: str
    sourceKind: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowSourceAssetResponse(BaseModel):
    assetType: str
    label: str | None = None
    mimeType: str | None = None
    assetUrl: str | None = None
    pageNumber: int | None = None
    width: int | None = None
    height: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowSourceSlideResponse(BaseModel):
    slideIndex: int
    title: str
    role: str
    rawText: str
    sourcePageNumber: int | None = None
    thumbnailPath: str | None = None
    thumbnailMimeType: str | None = None
    widthPoints: float | None = None
    heightPoints: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    blocks: list[WorkflowSourceBlockResponse] = Field(default_factory=list)
    assets: list[WorkflowSourceAssetResponse] = Field(default_factory=list)


class WorkflowSourceStateResponse(BaseModel):
    inputSourceId: str | None = None
    sourceVersionId: str | None = None
    fileSaved: bool
    extractionReady: bool
    slideCount: int
    assetCount: int
    thumbnailCount: int
    brandExtractionReady: bool
    sourceEnrichment: WorkflowSourceEnrichmentResponse | None = None
    slides: list[WorkflowSourceSlideResponse] = Field(default_factory=list)


class WorkflowSmartDeckStateResponse(BaseModel):
    workspaceId: str | None = None
    ready: bool
    sourceSlideCount: int
    generatedSlideCount: int
    activeDesignVersionId: str | None = None
    hasRenderableSchema: bool


class WorkflowProviderStateResponse(BaseModel):
    configured: bool
    blockingReason: WorkflowBlockingReason | None = None
    provider: str | None = None
    model: str | None = None


class WorkflowBrandStateResponse(BaseModel):
    profileId: str | None = None
    status: str = "idle"
    ready: bool = False
    sourceMode: str | None = None
    profile: dict[str, Any] | None = None


class WorkflowLinksResponse(BaseModel):
    processingUrl: str
    smartDeckUrl: str


class WorkflowPhaseResponse(BaseModel):
    key: str
    label: str
    description: str | None = None
    status: str
    active: bool | None = None
    completed: bool | None = None
    count: int | None = None


class DeckWorkflowStateResponse(BaseModel):
    deckId: str
    workflowId: str
    phase: WorkflowPhase
    activeStage: str | None = None
    stages: list[WorkflowPhaseResponse] = Field(default_factory=list)
    status: WorkflowJobStatus
    lifecycleStatus: str
    nextAction: WorkflowNextAction
    blockingReason: WorkflowBlockingReason | None = None
    message: str | None = None
    sourceFileStatus: str | None = None
    sourceFileSaved: bool = False
    deckExtractionStatus: str | None = None
    processingStage: str | None = None
    processingStageLabel: str | None = None
    workerState: str | None = None
    workerMessage: str | None = None
    retryUrl: str | None = None
    canRemove: bool = False
    canOpenSmartDeck: bool = False
    canGenerate: bool = False
    canRetry: bool = False
    degradedMode: bool = False
    missingArtifacts: list[str] = Field(default_factory=list)
    failures: list[dict[str, Any]] = Field(default_factory=list)
    workerHeartbeat: dict[str, Any] | None = None
    updatedAt: str | None = None
    activeJob: WorkflowJobSummaryResponse | None = None
    latestJobs: list[WorkflowJobSummaryResponse] = Field(default_factory=list)
    phases: list[WorkflowPhaseResponse] = Field(default_factory=list)
    source: WorkflowSourceStateResponse
    smartDeck: WorkflowSmartDeckStateResponse
    provider: WorkflowProviderStateResponse
    brand: WorkflowBrandStateResponse
    links: WorkflowLinksResponse


class SmartDeckReadinessStepsResponse(BaseModel):
    sourceFileSaved: bool = False
    slidesRead: bool = False
    previewsCreated: bool = False
    workspacePrepared: bool = False
    smartDeckOpenable: bool = False


class SmartDeckReadinessResponse(BaseModel):
    deckId: str
    ready: bool = False
    status: str
    currentStep: str
    canOpenSmartDeck: bool = False
    retryAllowed: bool = False
    blockingReason: str | None = None
    steps: SmartDeckReadinessStepsResponse
    adminDebugUrl: str
    processingUrl: str
    smartDeckUrl: str
    workflowStateUrl: str
    updatedAt: str | None = None
    message: str | None = None


class WorkflowJobResponse(BaseModel):
    jobId: str
    deckId: str
    workflowId: str
    jobType: WorkflowJobType
    status: WorkflowJobStatus
    phase: WorkflowPhase
    attemptCount: int | None = None
    maxAttempts: int | None = None
    recoveryCount: int | None = None
    priority: int | None = None
    idempotencyKey: str | None = None
    workerId: str | None = None
    progress: int | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    artifacts: list[WorkflowJobArtifactResponse] = Field(default_factory=list)
    error: WorkflowJobErrorResponse | None = None
    queuedAt: str | None = None
    startedAt: str | None = None
    heartbeatAt: str | None = None
    updatedAt: str | None = None
    lockedUntil: str | None = None
    lastRecoveredAt: str | None = None
    lastRecoveredBy: str | None = None
    completedAt: str | None = None
    failedAt: str | None = None
    publishedPhase: WorkflowPublishedPhase | None = None
    publishedAt: str | None = None
    terminal: bool = False
    terminalReason: str | None = None
    retryEligible: bool = False
    events: list[WorkflowJobEventResponse] = Field(default_factory=list)


class WorkflowCommandAcceptedResponse(BaseModel):
    accepted: bool = True
    jobId: str
    jobType: WorkflowJobType
    status: WorkflowJobStatus
    phase: WorkflowPhase
    workflowStateUrl: str
    jobUrl: str


class WorkflowSourceExtractionRequest(BaseModel):
    idempotencyKey: str | None = Field(default=None, max_length=255)


class WorkflowGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    selectedSourceSlideIds: list[str] = Field(min_length=1, max_length=20)
    idempotencyKey: str = Field(min_length=1, max_length=255)
    sourceVersionId: str | None = Field(default=None, max_length=120)
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
    detectedSubjects: list[dict[str, Any]] | None = None
    subjectConfidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_unique_selected_slides(self) -> "WorkflowGenerationRequest":
        if len(set(self.selectedSourceSlideIds)) != len(self.selectedSourceSlideIds):
            raise ValueError("selectedSourceSlideIds must not contain duplicates.")
        return self

    model_config = ConfigDict(populate_by_name=True)


class WorkflowLlmParallelizationRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    selectedSourceSlideIds: list[str] = Field(min_length=1, max_length=40)
    idempotencyKey: str = Field(min_length=1, max_length=255)
    partitionCount: int = Field(default=4, ge=1, le=32)
    batchSize: int = Field(default=8, ge=1, le=64)
    preferredModel: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_unique_selected_slides(self) -> "WorkflowLlmParallelizationRequest":
        if len(set(self.selectedSourceSlideIds)) != len(self.selectedSourceSlideIds):
            raise ValueError("selectedSourceSlideIds must not contain duplicates.")
        return self


class WorkflowApplyRequest(BaseModel):
    designVersionId: str = Field(min_length=1, max_length=120)
    idempotencyKey: str = Field(min_length=1, max_length=255)


class WorkflowExportRequest(BaseModel):
    type: str | None = Field(default=None, min_length=1, max_length=80)
    exportType: str | None = Field(default=None, min_length=1, max_length=80)
    idempotencyKey: str = Field(min_length=1, max_length=255)

    @property
    def normalized_type(self) -> str | None:
        return self.type or self.exportType


WorkflowCommandName = Literal[
    "start_source_extraction",
    "start_source_processing",
    "create_smart_deck",
    "retry",
    "generate_preview",
    "run_llm_parallelization",
    "apply_design_version",
    "export",
]


class WorkflowCommandRequest(BaseModel):
    command: WorkflowCommandName
    idempotencyKey: str | None = Field(default=None, max_length=255)
    generation: WorkflowGenerationRequest | None = None
    parallelization: WorkflowLlmParallelizationRequest | None = None
    apply: WorkflowApplyRequest | None = None
    export: WorkflowExportRequest | None = None
