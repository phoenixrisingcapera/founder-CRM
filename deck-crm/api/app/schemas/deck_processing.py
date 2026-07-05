from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel, Field

WorkflowJobType = Literal[
    "source_ingestion",
    "source_extraction",
    "miniatures",
    "brand_extraction",
    "smart_deck_context",
    "db_publisher",
    "llm_generation",
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


class DeckProcessingPhaseResponse(BaseModel):
    key: str
    label: str
    description: str | None = None
    status: str
    active: bool | None = None
    completed: bool | None = None
    count: int | None = None


class DeckProcessingUploadResponse(BaseModel):
    sourceSaved: bool
    fileId: str | None = None
    filename: str | None = None
    mimeType: str | None = None
    fileExtension: str | None = None
    storagePath: str | None = None
    storageProvider: str | None = None
    sizeBytes: int | None = None
    checksumSha256: str | None = None
    uploadedAt: str | None = None


class DeckProcessingRunResponse(BaseModel):
    id: str | None = None
    runId: str | None = None
    workflowJobId: str | None = None
    workflowJobType: WorkflowJobType | None = None
    workflowJobStatus: WorkflowJobStatus | None = None
    workflowPhase: str | None = None
    deckId: str
    sourceFileId: str | None = None
    runType: str
    status: WorkflowJobStatus
    runStatus: WorkflowJobStatus | None = None
    state: str | None = None
    stage: str | None = None
    stageLabel: str | None = None
    nextAction: str | None = None
    attemptCount: int | None = None
    maxAttempts: int | None = None
    recoveryCount: int | None = None
    lockedBy: str | None = None
    lockedAt: str | None = None
    heartbeatAt: str | None = None
    lastRecoveredAt: str | None = None
    lastRecoveredBy: str | None = None
    publishedPhase: str | None = None
    publishedAt: str | None = None
    requiresManualReview: bool = False
    finalFailureReason: str | None = None
    slideCount: int | None = None
    blockCount: int | None = None
    assetCount: int | None = None
    errorMessage: str | None = None
    errorJson: dict[str, Any] | None = None
    metadataJson: dict[str, Any] | None = None
    metricsJson: dict[str, Any] | None = None
    createdAt: str | None = None
    startedAt: str | None = None
    completedAt: str | None = None


class DeckProcessingOutputCountsResponse(BaseModel):
    slideCount: int
    blockCount: int
    assetCount: int
    previewCount: int


class DeckProcessingWorkerResponse(BaseModel):
    workerRequired: bool = False
    state: str
    queueState: WorkflowJobStatus | None = None
    runId: str | None = None
    workflowJobId: str | None = None
    workflowJobType: WorkflowJobType | None = None
    workflowJobStatus: WorkflowJobStatus | None = None
    recoveryCount: int | None = None
    queuedTooLong: bool = False
    heartbeatStale: bool = False
    staleReason: str | None = None
    message: str | None = None
    oldestQueuedAt: str | None = None
    lastHeartbeatAt: str | None = None
    lastRecoveredAt: str | None = None
    lastRecoveredBy: str | None = None
    queuedAgeSeconds: int | None = None
    heartbeatAgeSeconds: int | None = None


class DeckProcessingVisibilityResponse(BaseModel):
    deckId: str
    workflowId: str | None = None
    workflowPhase: str | None = None
    workflowStatus: WorkflowJobStatus | None = None
    status: str
    state: str
    deckStatus: str
    deckSummary: str | None = None
    upload: DeckProcessingUploadResponse
    processing: DeckProcessingRunResponse | None = None
    outputs: DeckProcessingOutputCountsResponse
    worker: DeckProcessingWorkerResponse
    nextAction: str
    canOpenSmartDeck: bool = False
    canRetry: bool = False
    canRemove: bool = False
    phases: list[DeckProcessingPhaseResponse] = Field(default_factory=list)
    processingStatusUrl: str | None = None
    smartDeckUrl: str | None = None
    retryUrl: str | None = None


class SmartDeckProcessingStartResponse(BaseModel):
    ok: bool
    deck_id: str
    workflowId: str | None = None
    workflowPhase: str | None = None
    workflowStatus: WorkflowJobStatus | None = None
    workflowJobId: str | None = None
    workflowJobType: WorkflowJobType | None = None
    workflowJobStatus: WorkflowJobStatus | None = None
    status: WorkflowJobStatus | None = None
    state: WorkflowJobStatus | None = None
    deckStatus: WorkflowJobStatus | None = None
    processing: DeckProcessingRunResponse
    background_started: bool
    worker_required: bool = False
    next_action: str
    processing_status_url: str
    smart_deck_url: str
