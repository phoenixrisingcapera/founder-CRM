import { isApiAuthError, readApiJsonOrThrow } from '$lib/api/apiError';
import { deckSmartDeckReadinessApiPath, deckWorkflowJobApiPath, deckWorkflowStateApiPath } from '$lib/contracts';
import type { BrandProfile } from '$lib/types/deckService-brand';
import type { DesignVersion, SmartDeckWorkspacePayload } from '$lib/api/smartDeckWorkspace';
export type DeckExtractionStatus = 'idle' | 'queued' | 'processing' | 'ready' | 'failed';
type DeckProcessingLifecycleStatus = 'idle' | 'queued' | 'processing' | 'ready' | 'failed' | 'unknown';
export type WorkflowJobType =
  | 'source_ingestion'
  | 'source_extraction'
  | 'miniatures'
  | 'brand_extraction'
  | 'smart_deck_context'
  | 'db_publisher'
  | 'llm_generation'
  | 'schema_validation'
  | 'preview_render'
  | 'apply_version'
  | 'export';

export type WorkflowJobStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed_retryable'
  | 'failed_final'
  | 'blocked'
  | 'timed_out';

type WorkflowNextAction =
  | 'continue_upload'
  | 'view_processing'
  | 'apply_preview'
  | 'open_smart_deck'
  | 'configure_provider'
  | 'create_smart_deck';

const DEFAULT_AUTH_EXPIRED_MESSAGE = 'Your session expired. Sign in again to continue processing this deck.';

let deckProcessingAuthExpired = false;
let deckProcessingAuthExpiredMessage = DEFAULT_AUTH_EXPIRED_MESSAGE;
let deckProcessingAuthExpiredPath: string | undefined;

class DeckProcessingAuthExpiredError extends Error {
  status = 401;
  actionLabel = 'Sign in again';

  constructor(message = deckProcessingAuthExpiredMessage, readonly path?: string) {
    super(message || DEFAULT_AUTH_EXPIRED_MESSAGE);
    this.name = 'DeckProcessingAuthExpiredError';
  }
}

function rememberAuthExpired(error: unknown, path?: string): DeckProcessingAuthExpiredError | null {
  if (!isApiAuthError(error) && !(error instanceof DeckProcessingAuthExpiredError)) {
    return null;
  }

  deckProcessingAuthExpired = true;
  deckProcessingAuthExpiredMessage = error instanceof Error && error.message ? error.message : DEFAULT_AUTH_EXPIRED_MESSAGE;
  deckProcessingAuthExpiredPath = path;
  return new DeckProcessingAuthExpiredError(deckProcessingAuthExpiredMessage, deckProcessingAuthExpiredPath);
}

function assertDeckProcessingAuthAvailable() {
  if (deckProcessingAuthExpired) {
    throw new DeckProcessingAuthExpiredError(deckProcessingAuthExpiredMessage, deckProcessingAuthExpiredPath);
  }
}

async function readDeckPollingJsonOrThrow<T>(response: Response, fallbackMessage: string, path?: string): Promise<T> {
  try {
    return await readApiJsonOrThrow<T>(response, fallbackMessage, path);
  } catch (error) {
    const authError = rememberAuthExpired(error, path);
    if (authError) {
      throw authError;
    }
    throw error;
  }
}

export interface SourceEnrichmentStatus {
  source: string;
  llmStatus?: string;
  provider?: string;
  model?: string;
  message: string;
  badge: string;
}

export interface WorkflowSourceBlock {
  blockIndex: number;
  rawText: string;
  normalizedText: string;
  blockType: string;
  sourceKind?: string | null;
  metadata: Record<string, unknown>;
}

export interface WorkflowSourceAsset {
  assetType: string;
  label?: string | null;
  mimeType?: string | null;
  assetUrl?: string | null;
  pageNumber?: number | null;
  width?: number | null;
  height?: number | null;
  metadata: Record<string, unknown>;
}

export interface WorkflowSourceSlide {
  slideIndex: number;
  title: string;
  role: string;
  rawText: string;
  sourcePageNumber?: number | null;
  thumbnailPath?: string | null;
  thumbnailMimeType?: string | null;
  widthPoints?: number | null;
  heightPoints?: number | null;
  metadata: Record<string, unknown>;
  blocks: WorkflowSourceBlock[];
  assets: WorkflowSourceAsset[];
}

export interface ProcessingPhase {
  key: string;
  label: string;
  description?: string;
  status: 'pending' | 'active' | 'completed' | 'failed' | string;
  active?: boolean;
  completed?: boolean;
  count?: number | null;
}

export type WorkflowFailure = Record<string, unknown>;

export interface SmartDeckProcessingStatus {
  deckId: string;
  status: DeckProcessingLifecycleStatus;
  brandProfile?: BrandProfile | null;
  nextAction?: WorkflowNextAction;
  activeStage?: string | null;
  updatedAt?: string | null;
  processingStage?: string | null;
  processingStageLabel?: string | null;
  sourceFileStatus?: string;
  sourceFileSaved: boolean;
  sourceEnrichment?: SourceEnrichmentStatus | null;
  sourceSlides?: WorkflowSourceSlide[];
  deckExtractionStatus: DeckExtractionStatus;
  latestConfirmation?: Record<string, unknown> | null;
  message?: string;
  errorMessage?: string;
  phases: ProcessingPhase[];
  stages: ProcessingPhase[];
  canOpenSmartDeck: boolean;
  canGenerate?: boolean;
  canRetry: boolean;
  missingArtifacts?: string[];
  failures?: WorkflowFailure[];
  workerHeartbeat?: Record<string, unknown> | null;
}

export interface SmartDeckProcessingBackendDiagnostics {
  backendStatus?: number;
  backendStatusText?: string;
  backendMessage?: string;
  backendPath?: string;
  backendPayload?: Record<string, unknown> | null;
}

export interface SmartDeckProcessingStatusWithDiagnostics
  extends SmartDeckProcessingStatus,
    SmartDeckProcessingBackendDiagnostics {}

export interface SmartDeckReadinessSteps {
  sourceFileSaved: boolean;
  slidesRead: boolean;
  previewsCreated: boolean;
  workspacePrepared: boolean;
  smartDeckOpenable: boolean;
}

export interface SmartDeckReadinessStatus {
  deckId: string;
  ready: boolean;
  status: string;
  currentStep: string;
  canOpenSmartDeck: boolean;
  retryAllowed: boolean;
  blockingReason?: string | null;
  steps: SmartDeckReadinessSteps;
  adminDebugUrl?: string;
  processingUrl?: string;
  smartDeckUrl?: string;
  workflowStateUrl?: string;
  updatedAt?: string | null;
  message?: string;
}

function getRecord(payload: unknown): Record<string, unknown> {
  return payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : {};
}

function nullableRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function firstString(...values: unknown[]) {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return undefined;
}

function firstBoolean(...values: unknown[]) {
  for (const value of values) {
    if (typeof value === 'boolean') return value;
  }
  return undefined;
}

function isSavedLike(value: unknown) {
  return value === true || value === 'saved' || value === 'ready' || value === 'uploaded' || value === 'available';
}

function parseTimestamp(value: unknown): number | null {
  if (typeof value !== 'string' || !value.trim()) return null;
  const timestamp = new Date(value).getTime();
  return Number.isFinite(timestamp) ? timestamp : null;
}

export function getWorkflowStatusAgeMinutes(status: SmartDeckProcessingStatus | null | undefined): number | null {
  const timestamp = parseTimestamp(status?.updatedAt);
  if (timestamp === null) return null;
  return Math.max(0, Math.round((Date.now() - timestamp) / 60000));
}

export function isWorkflowStatusStalled(status: SmartDeckProcessingStatus | null | undefined, thresholdMinutes = 12): boolean {
  if (!status) return false;
  if (!['processing', 'queued'].includes(status.status)) return false;
  const ageMinutes = getWorkflowStatusAgeMinutes(status);
  return ageMinutes !== null && ageMinutes >= thresholdMinutes;
}

export function getWorkflowActivePhaseLabel(status: SmartDeckProcessingStatus | null | undefined): string | null {
  if (!status) return null;
  if (status.activeStage) {
    const explicit = status.stages.find((phase) => phase.key === status.activeStage);
    if (explicit) {
      return explicit.label || explicit.key || null;
    }
  }
  const activePhase = status.phases.find((phase) => phase.active || phase.status === 'active');
  if (!activePhase) return null;
  return activePhase.label || activePhase.key || null;
}

export function normalizeSmartDeckProcessingStatus(payload: unknown, deckId: string): SmartDeckProcessingStatus {
  const record = getRecord(payload);
  const source = getRecord(record.source);
  const brand = getRecord(record.brand);
  const nextAction = firstString(record.nextAction) as WorkflowNextAction | undefined;
  const activeStage = firstString(record.activeStage, record.processingStage, record.phase);
  const status = (firstString(record.lifecycleStatus, record.status) ?? 'unknown') as DeckProcessingLifecycleStatus;
  const sourceFileStatus = firstString(record.sourceFileStatus) ?? (isSavedLike(record.sourceFileSaved) ? 'saved' : 'missing');
  const sourceFileSaved =
    firstBoolean(record.sourceFileSaved) ??
    isSavedLike(sourceFileStatus);
  const sourceEnrichment = (source.sourceEnrichment ?? null) as SourceEnrichmentStatus | null;
  const sourceSlides = Array.isArray(source.slides)
    ? (source.slides as WorkflowSourceSlide[])
    : [];
  const brandProfile = brand.profile && typeof brand.profile === 'object' ? (brand.profile as BrandProfile) : null;
  const phases = Array.isArray(record.phases) ? (record.phases as ProcessingPhase[]) : [];
  const stages = Array.isArray(record.stages) ? (record.stages as ProcessingPhase[]) : phases;
  const failures = Array.isArray(record.failures) ? (record.failures as WorkflowFailure[]) : [];
  const missingArtifacts = Array.isArray(record.missingArtifacts)
    ? record.missingArtifacts.filter((value): value is string => typeof value === 'string' && value.trim().length > 0).map((value) => value.trim())
    : [];

  return {
    deckId: firstString(record.deckId) ?? deckId,
    status,
    brandProfile,
    nextAction,
    activeStage,
    updatedAt: firstString(record.updatedAt, record.updated_at, record.updatedAtIso, record.updated_at_iso),
    processingStage: activeStage,
    processingStageLabel: firstString(record.processingStageLabel, record.processing_stage_label, record.stageLabel, record.stage_label),
    sourceFileStatus,
    sourceFileSaved,
    sourceEnrichment,
    sourceSlides,
    deckExtractionStatus: (firstString(record.deckExtractionStatus) ?? 'idle') as DeckExtractionStatus,
    latestConfirmation: nullableRecord(record.latestConfirmation ?? record.latest_confirmation),
    message: firstString(record.message, record.nextStepMessage),
    errorMessage: firstString(record.errorMessage, record.error),
    phases,
    stages,
    canOpenSmartDeck: firstBoolean(record.canOpenSmartDeck) ?? false,
    canGenerate: firstBoolean(record.canGenerate) ?? undefined,
    canRetry: firstBoolean(record.canRetry) ?? false,
    missingArtifacts,
    failures,
    workerHeartbeat: nullableRecord(record.workerHeartbeat),
  };
}

async function getDeckWorkflowState(deckId: string): Promise<unknown> {
  assertDeckProcessingAuthAvailable();
  const path = deckWorkflowStateApiPath(deckId);
  const response = await fetch(path);
  return readDeckPollingJsonOrThrow<unknown>(response, 'Could not load deck workflow state.', path);
}

async function getSmartDeckReadinessState(deckId: string): Promise<unknown> {
  assertDeckProcessingAuthAvailable();
  const path = deckSmartDeckReadinessApiPath(deckId);
  const response = await fetch(path);
  return readDeckPollingJsonOrThrow<unknown>(response, 'Could not load Smart Deck readiness.', path);
}

async function getWorkflowJob(jobId: string): Promise<{ jobId: string; status: WorkflowJobStatus; error?: { message: string } | null }> {
  assertDeckProcessingAuthAvailable();
  const path = deckWorkflowJobApiPath(jobId);
  const response = await fetch(path);
  return readDeckPollingJsonOrThrow<{ jobId: string; status: WorkflowJobStatus; error?: { message: string } | null }>(
    response,
    'Could not load workflow job.',
    path
  );
}

export interface WorkflowJobCompletionResult {
  jobId: string;
  status: WorkflowJobStatus;
  error?: { message: string } | null;
  errorMessage?: string | null;
  artifacts?: Array<Record<string, unknown>> | null;
  designVersion?: DesignVersion | null;
  workspace?: SmartDeckWorkspacePayload | null;
}

function delayMs(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function waitForWorkflowJobCompletion(
  jobId: string,
  failureMessage: string,
  maxAttempts = 40,
  pollDelayMs = 250
): Promise<WorkflowJobCompletionResult> {
  let attempt = 0;
  while (attempt < maxAttempts) {
    const job = await getWorkflowJob(jobId);
    const status = String(job.status ?? '');
    if (status === 'completed') {
      return job;
    }
    if (status === 'failed_retryable' || status === 'failed_final' || status === 'blocked' || status === 'timed_out') {
      throw new Error(job.error?.message || failureMessage);
    }
    attempt += 1;
    await delayMs(pollDelayMs);
  }
  throw new Error(`Timed out waiting for workflow job ${jobId} to complete.`);
}

export async function getDeckWorkflowStatus(deckId: string): Promise<SmartDeckProcessingStatus> {
  const payload = await getDeckWorkflowState(deckId);
  return normalizeSmartDeckProcessingStatus(payload, deckId);
}

export function normalizeSmartDeckReadiness(payload: unknown, deckId: string): SmartDeckReadinessStatus {
  const record = getRecord(payload);
  const stepsRecord = getRecord(record.steps);
  return {
    deckId: firstString(record.deckId) ?? deckId,
    ready: firstBoolean(record.ready) ?? false,
    status: firstString(record.status) ?? 'unknown',
    currentStep: firstString(record.currentStep) ?? 'checking_smart_deck_readiness',
    canOpenSmartDeck: firstBoolean(record.canOpenSmartDeck) ?? false,
    retryAllowed: firstBoolean(record.retryAllowed) ?? false,
    blockingReason: firstString(record.blockingReason) ?? null,
    steps: {
      sourceFileSaved: firstBoolean(stepsRecord.sourceFileSaved) ?? false,
      slidesRead: firstBoolean(stepsRecord.slidesRead) ?? false,
      previewsCreated: firstBoolean(stepsRecord.previewsCreated) ?? false,
      workspacePrepared: firstBoolean(stepsRecord.workspacePrepared) ?? false,
      smartDeckOpenable: firstBoolean(stepsRecord.smartDeckOpenable) ?? false,
    },
    adminDebugUrl: firstString(record.adminDebugUrl),
    processingUrl: firstString(record.processingUrl),
    smartDeckUrl: firstString(record.smartDeckUrl),
    workflowStateUrl: firstString(record.workflowStateUrl),
    updatedAt: firstString(record.updatedAt, record.updated_at) ?? null,
    message: firstString(record.message),
  };
}

export async function getSmartDeckReadiness(deckId: string): Promise<SmartDeckReadinessStatus> {
  const payload = await getSmartDeckReadinessState(deckId);
  return normalizeSmartDeckReadiness(payload, deckId);
}
