import type { DesignBatchPreview } from '@deck-aistack-codes/shared';
import { deckProductApiPath } from '$lib/contracts';
import type {
  SmartDeckDeckType,
  SmartDeckGenerationTopicRequest,
  SmartDeckSubject,
  SmartDeckSubjectDetection
} from '$lib/types/smart-deck-subjects';
import { waitForWorkflowJobCompletion } from '$lib/api/deckService/workflow.client';

export { waitForWorkflowJobCompletion };

export type SmartDeckGenerationStatus = 'idle' | 'running' | 'ready' | 'failed';

export type SmartDeckSaveStatus = 'idle' | 'saving' | 'saved' | 'failed';
type GeneratedSlideValidationStatus = 'valid' | 'warning' | 'invalid' | 'unknown';

interface RenderSchemaElement {
  id: string;
  type: 'text' | 'shape' | 'image' | 'chart_placeholder';
  text?: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex?: number | null;
  fontSize?: number | null;
  fontWeight?: string | null;
  colorToken?: string | null;
  fillToken?: string | null;
  assetUrl?: string | null;
  analyticsKey?: string | null;
}

interface RenderSchemaBackgroundLayer {
  id: string;
  type: 'shape' | 'image';
  shape?: 'rectangle' | 'circle' | 'line' | null;
  role?: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex?: number;
  style?: {
    fill?: string | null;
    opacity?: number | null;
    radius?: number | null;
  } | null;
  assetUrl?: string | null;
}

export interface RenderSchema {
  schemaVersion: 'smart-deck-render-schema.v1';
  width: number;
  height: number;
  background: {
    type: 'token' | 'color' | 'gradient' | 'image' | 'layered';
    value?: string | null;
    fill?: string | null;
    layers?: RenderSchemaBackgroundLayer[];
  };
  brandTokensUsed?: string[];
  analytics?: {
    slidePurpose?: string | null;
    audience?: string | null;
    sourceFactIds?: string[];
    sourceFactsUsed?: string[];
    assumptions?: string[];
    missingInputs?: string[];
    qualityWarnings?: string[];
    confidence?: number | null;
    trackedEvents?: string[];
  };
  exportMetadata?: {
    exportReady?: boolean;
    renderer?: 'smart_deck_scene_graph';
    supportedFormats?: string[];
  };
  elements: RenderSchemaElement[];
}

interface GeneratedSlideElementVersion {
  id: string;
  elementId: string;
  generatedSlideId: string;
  designVersionId: string;
  versionNumber: number;
  source: string;
  status: string;
  style?: Record<string, unknown> | null;
  content?: Record<string, unknown> | null;
  changeSummary?: string | null;
  createdAt: string;
}

interface GeneratedSlideElement {
  id: string;
  generatedSlideId: string;
  deckId: string;
  designVersionId: string;
  sourceSlideId?: string | null;
  elementKey: string;
  elementType: string;
  parentElementId?: string | null;
  zIndex: number;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  locked: boolean;
  visible: boolean;
  style?: Record<string, unknown> | null;
  content?: Record<string, unknown> | null;
  versions: GeneratedSlideElementVersion[];
  createdAt: string;
  updatedAt: string;
}

export interface SmartDeckSourceSlide {
  id: string;
  deckId: string;
  slideNumber: number;
  title: string;
  extractedText: string;
  thumbnailUrl?: string | null;
  previewImageUrl?: string | null;
  layoutHints?: Record<string, unknown>;
  blocks?: unknown[];
}

interface SmartDeckWorkspaceState {
  id: string;
  deckId: string;
  userId?: string | null;
  activeDesignVersionId?: string | null;
  activeSourceSlideId?: string | null;
  activeGeneratedSlideId?: string | null;
  selectedElementId?: string | null;
  status: 'ready' | 'generating' | 'reviewing' | 'failed' | string;
  createdAt: string;
  updatedAt: string;
}

interface SmartDeckPreferences {
  id: string;
  workspaceId: string;
  deckId: string;
  selectedSourceSlideIds: string[];
  activeSourceSlideId?: string | null;
  activeDesignVersionId?: string | null;
  activeGeneratedSlideId?: string | null;
  selectedElementId?: string | null;
  audience?: string | null;
  deckType?: SmartDeckDeckType | null;
  preferredModel?: string | null;
  selectedSubject?: SmartDeckSubject | null;
  selectedActionId?: string | null;
  zoomLevel: number;
  canvasFitMode: 'fit' | 'fill' | 'actual_size';
  rightPanelOpen: boolean;
  slideRailOpen: boolean;
  updatedAt: string;
}

export interface SmartDeckChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
  selectedSourceSlideIds?: string[];
  generationBatchId?: string | null;
  metadata?: Record<string, unknown> | null;
}

interface BackendGeneratedSlide {
  id: string;
  deckId: string;
  designVersionId: string;
  generationJobId?: string | null;
  sourceSlideId?: string | null;
  slideNumber: number;
  title: string;
  status: string;
  renderSchema: Record<string, unknown>;
  designTokens?: Record<string, string> | null;
  previewImageUrl?: string | null;
  validationStatus: GeneratedSlideValidationStatus | string;
  elements?: GeneratedSlideElement[];
  createdAt: string;
  updatedAt: string;
}

export interface DesignVersion {
  id: string;
  deckId: string;
  generationJobId?: string | null;
  name: string;
  status: string;
  isActive: boolean;
  summary?: string | null;
  generatedSlides: BackendGeneratedSlide[];
  createdAt: string;
  updatedAt: string;
}

export interface SmartDeckWorkspacePayload {
  deck: {
    id: string;
    workspaceId?: string | null;
    title: string;
    status: string;
    audience?: string | null;
    purpose?: string | null;
    summary?: string | null;
  };
  workspace: SmartDeckWorkspaceState;
  preferences: SmartDeckPreferences;
  messages: SmartDeckChatMessage[];
  designTokens: Array<Record<string, unknown>>;
  sourceSlides: SmartDeckSourceSlide[];
  generationJobs: Array<{
    id: string;
    deckId: string;
    status: string;
    prompt: string;
    selectedSourceSlideIds: string[];
    createdAt: string;
  }>;
  designVersions: DesignVersion[];
  activeDesignVersionId?: string | null;
  activeSourceSlideId?: string | null;
  activeGeneratedSlideId?: string | null;
  generatedSlides: BackendGeneratedSlide[];
  knowledgeMetadata?: Record<string, unknown> | null;
  runtimeContext?: Record<string, unknown> | null;
  runtimeCapabilities?: {
    schemaVersion?: string;
    knowledgeMetadata?: Record<string, unknown>;
    productBoundary?: Record<string, unknown>;
    llmTasks?: Array<{
      key: string;
      inputs: string[];
      outputs: string[];
    }>;
    guardrailGroups?: Array<{
      group: string;
      rules: string[];
    }>;
    llmExtensions?: string[];
    schemas?: string[];
    prompts?: string[];
    enabledSmartDeckCapabilities?: string[];
    instructions?: string[];
  } | null;
}

export interface SmartDeckGenerationInput {
  prompt: string;
  selectedSourceSlideIds: string[];
  activeSourceSlideId?: string | null;
  selectedElementId?: string | null;
  deckType?: SmartDeckDeckType;
  audience?: string | null;
  preferredModel?: string | null;
  selectedSubject?: SmartDeckSubject | null;
  detectedSubjects?: SmartDeckSubjectDetection[];
  actionId?: string | null;
  actionPrompt?: string | null;
  userPrompt?: string | null;
  latestBatchId?: string | null;
}

interface SmartDeckGenerationResponse {
  runId: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  generationJob: SmartDeckWorkspacePayload['generationJobs'][number];
  designVersion?: DesignVersion | null;
  workspace?: SmartDeckWorkspacePayload | null;
}

export interface SmartDeckGenerationWorkflowResult {
  jobId: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'failed_retryable' | 'failed_final' | 'blocked' | 'timed_out';
  error?: { message: string } | null;
  errorMessage?: string | null;
  artifacts?: Array<Record<string, unknown>> | null;
  designVersion?: DesignVersion | null;
  workspace?: SmartDeckWorkspacePayload | null;
}

interface ElementVariationJob {
  id: string;
  deckId: string;
  workspaceId: string;
  generatedSlideId: string;
  elementId: string;
  baseElementVersionId?: string | null;
  instruction: string;
  variationCount: number;
  status: string;
  outputElementVersionId?: string | null;
  errorMessage?: string | null;
  createdAt: string;
  startedAt?: string | null;
  completedAt?: string | null;
}

export interface GeneratedSlideCode {
  generatedSlideId: string;
  schemaJson: RenderSchema;
  renderSchema: RenderSchema;
  designTokens?: Record<string, string> | null;
  validationStatus: GeneratedSlideValidationStatus;
  validationMessages: string[];
}

export async function getSmartDeckWorkspace(deckId: string): Promise<SmartDeckWorkspacePayload> {
  return requestJson<SmartDeckWorkspacePayload>(`/api/decks/${deckId}/smart-deck`);
}

export async function getGeneratedSlideCode(deckId: string, generatedSlideId: string): Promise<GeneratedSlideCode> {
  const payload = await requestJson<{
    codeVersion: {
      generatedSlideId: string;
      renderSchema: RenderSchema;
      status: GeneratedSlideValidationStatus;
      validationErrors?: Array<Record<string, unknown>>;
    };
    generatedSlide: {
      designTokens?: Record<string, string> | null;
    };
  }>(`/api/decks/${deckId}/generated-slides/${generatedSlideId}/code`);

  return {
    generatedSlideId: payload.codeVersion.generatedSlideId,
    schemaJson: payload.codeVersion.renderSchema,
    renderSchema: payload.codeVersion.renderSchema,
    designTokens: payload.generatedSlide.designTokens ?? null,
    validationStatus: payload.codeVersion.status,
    validationMessages: payload.codeVersion.validationErrors?.map((item) => JSON.stringify(item)) ?? ['render schema is valid']
  };
}

export async function startSmartDeckGenerationWorkflow(
  deckId: string,
  input: SmartDeckGenerationInput
): Promise<SmartDeckGenerationResponse> {
  return requestJson<SmartDeckGenerationResponse>(deckProductApiPath(`/decks/${deckId}/workflows/smart-deck-generation`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(input)
  });
}

export async function createElementVariationJob(
  deckId: string,
  generatedSlideId: string,
  elementId: string,
  input: {
    instruction: string;
    variationCount?: number;
  }
): Promise<{
  variationJob: {
    id: string;
    generatedSlideId: string;
  };
  element: {
    id: string;
  };
  generatedSlide?: {
    id: string;
  } | null;
  designVersion?: DesignVersion | null;
  workspace?: SmartDeckWorkspacePayload | null;
}> {
  return requestJson(`/api/decks/${deckId}/generated-slides/${generatedSlideId}/elements/${elementId}/variation-jobs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(input)
  });
}

export async function applyDesignVersion(
  deckId: string,
  versionId: string
): Promise<{ versionId: string; status: 'saved' }> {
  const payload = await requestJson<{ jobId?: string }>(deckProductApiPath(`/decks/${deckId}/workflows/apply-design-version`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      designVersionId: versionId
    })
  });
  if (!payload.jobId) {
    throw new Error('Design version apply did not return a workflow job id.');
  }
  await waitForWorkflowJobCompletion(payload.jobId, 'Design version apply failed.');
  return {
    versionId,
    status: 'saved'
  };
}

export async function discardDesignVersion(deckId: string, versionId: string): Promise<DesignVersion[]> {
  const payload = await requestJson<{ designVersions: DesignVersion[] }>(
    `/api/decks/${deckId}/design-versions/${versionId}/discard`,
    { method: 'POST' }
  );
  return payload.designVersions;
}

export async function restoreDesignVersion(deckId: string, versionId: string): Promise<DesignVersion[]> {
  const payload = await requestJson<{ designVersions: DesignVersion[] }>(
    `/api/decks/${deckId}/design-versions/${versionId}/restore`,
    { method: 'POST' }
  );
  return payload.designVersions;
}

export async function updateSmartDeckSelection(
  deckId: string,
  input: {
    activeSourceSlideId?: string | null;
    activeGeneratedSlideId?: string | null;
    selectedElementId?: string | null;
  }
): Promise<SmartDeckWorkspacePayload['preferences']> {
  return requestJson(`/api/decks/${deckId}/smart-deck/selection`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(input)
  });
}

export async function patchSmartDeckPreferences(
  deckId: string,
  input: Partial<SmartDeckWorkspacePayload['preferences']>
): Promise<SmartDeckWorkspacePayload['preferences']> {
  return requestJson(`/api/decks/${deckId}/smart-deck/preferences`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(input)
  });
}

async function readJson<T>(response: Response): Promise<T> {
  return (await response.json()) as T;
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return readJson<T>(response);
}
