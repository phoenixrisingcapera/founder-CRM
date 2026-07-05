import { error, redirect } from '@sveltejs/kit';
import { BACKEND_URL } from '$server/backendApi';
import { deckProductApiPath } from '$lib/contracts';
import type {
  DeckShellProperties,
  DeckWorkspaceModel,
  DeckWorkspacePreferences,
  DesignBatchDetail,
  DesignBatchPreview,
  SaveConfirmation
} from '@deck-aistack-codes/shared';
import type { DeckGraph } from '$types/domain';
import { getDeckWorkspaceModel } from '$server/services/generatedWorkspaceService';
import { getDeckWorkspacePreferences } from '$server/services/shellWorkspaceService';
import { loadDeckGraph } from '$server/services/deckService';
import { getDesignBatchById, listLatestDesignBatches } from '$server/services/designBatchService';

const EMPTY_AI_PROVIDER_SUMMARY = {
  provider: null,
  preferredModel: null,
  apiKeyLast4: null,
  isConfigured: false,
  configuredAt: null,
  skippedAt: null
};

const HARD_ACCESS_FAILURE_STATUSES = new Set([401, 403, 404]);

type DegradedIssue = {
  key: string;
  label: string;
  message: string;
  status?: number;
  requestId?: string | null;
  ticketId?: string | null;
};

type SmartDeckWorkspaceStatus = {
  status: 'ready' | 'degraded';
  backendStatus: number;
  message: string | null;
  actionHref?: string;
  actionLabel?: string;
  issues?: DegradedIssue[];
};

type SmartDeckDebug = {
  processingNextAction: string | null;
  canOpenSmartDeck: boolean;
  generatedSlideCount: number;
  sourceSlideCount: number;
  activeDesignVersionId: string | null;
  activeGeneratedSlideId: string | null;
  renderSchemaElementCount: number;
  hasRenderableSchema: boolean;
  hasSourceSlides: boolean;
  workspaceStatus: string | null;
};

function getRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function getArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item) => item && typeof item === 'object') as Record<string, unknown>[] : [];
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }

  return null;
}

function firstNumber(...values: unknown[]): number | null {
  for (const value of values) {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value === 'string' && value.trim() && Number.isFinite(Number(value))) return Number(value);
  }

  return null;
}

function processingNextAction(payload: unknown): string | null {
  const record = getRecord(payload);
  const processing = getRecord(record.processing);
  const smartDeck = getRecord(record.smartDeck);
  const value =
    record.nextAction ??
    record.next_action ??
    processing.nextAction ??
    processing.next_action ??
    smartDeck.processingNextAction ??
    smartDeck.nextAction;
  return typeof value === 'string' ? value : null;
}

function processingSmartDeckDebug(payload: unknown): Record<string, unknown> {
  const record = getRecord(payload);
  return getRecord(record.smartDeck);
}

function smartDeckIsReady(payload: unknown): boolean {
  const record = getRecord(payload);
  return record.canOpenSmartDeck === true;
}

function getPayloadMessage(payload: unknown, fallback: string): string {
  const record = getRecord(payload);
  const detail = getRecord(record.detail);
  return (
    firstString(
      record.message,
      record.error,
      record.reason,
      detail.message,
      detail.error,
      detail.reason,
      typeof record.detail === 'string' ? record.detail : null
    ) ?? fallback
  );
}

function getPayloadRequestId(response: Response | null, payload: unknown): string | null {
  const record = getRecord(payload);
  const detail = getRecord(record.detail);
  return firstString(record.requestId, record.request_id, detail.requestId, detail.request_id, response?.headers.get('x-request-id'));
}

function getPayloadTicketId(payload: unknown): string | null {
  const record = getRecord(payload);
  const detail = getRecord(record.detail);
  return firstString(record.ticketId, record.ticket_id, detail.ticketId, detail.ticket_id);
}

function formatIssueMessage(message: string, issue: Pick<DegradedIssue, 'requestId' | 'ticketId'>): string {
  const suffix = [issue.requestId ? `request ${issue.requestId}` : null, issue.ticketId ? `ticket ${issue.ticketId}` : null]
    .filter(Boolean)
    .join(', ');

  return suffix ? `${message} (${suffix})` : message;
}

async function buildIssue(
  key: string,
  label: string,
  response: Response | null,
  fallback: string
): Promise<DegradedIssue> {
  const payload = await response?.json().catch(() => null);
  const issue = {
    key,
    label,
    message: getPayloadMessage(payload, fallback),
    status: response?.status,
    requestId: getPayloadRequestId(response, payload),
    ticketId: getPayloadTicketId(payload)
  } satisfies DegradedIssue;

  return {
    ...issue,
    message: formatIssueMessage(issue.message, issue)
  };
}

async function readJsonOrNull(response: Response | null): Promise<unknown> {
  if (!response?.ok) return null;
  return response.json().catch(() => null);
}

async function fetchOrNull(fetcher: typeof fetch, path: string, init?: RequestInit): Promise<Response | null> {
  return fetcher(path, init).catch(() => null);
}

async function loadProcessingVisibility(fetcher: typeof fetch, deckId: string): Promise<unknown> {
  const response = await fetchOrNull(fetcher, deckProductApiPath(`/decks/${deckId}/workflow-state`));
  return readJsonOrNull(response);
}

async function loadDeckProperties(fetcher: typeof fetch, deckId: string): Promise<DeckShellProperties | null> {
  const response = await fetchOrNull(fetcher, `/api/decks/${deckId}/properties`);
  if (!response?.ok) return null;
  const payload = await response.json().catch(() => null);
  return payload && typeof payload === 'object' && 'properties' in payload ? (payload as { properties?: DeckShellProperties }).properties ?? null : null;
}

function workspaceGeneratedSlides(workspace: unknown): Record<string, unknown>[] {
  const record = getRecord(workspace);
  const directSlides = getArray(record.generatedSlides ?? record.generated_slides);
  if (directSlides.length > 0) return directSlides;

  const designVersions = getArray(record.designVersions ?? record.design_versions);
  return designVersions.flatMap((version) => getArray(version.generatedSlides ?? version.generated_slides));
}

function workspaceSourceSlides(workspace: unknown): Record<string, unknown>[] {
  const record = getRecord(workspace);
  return getArray(record.sourceSlides ?? record.source_slides);
}

function workspaceHasSourceSlides(workspace: unknown): boolean {
  return workspaceSourceSlides(workspace).length > 0;
}

function workspaceHasRenderableSchema(workspace: unknown): boolean {
  const slides = workspaceGeneratedSlides(workspace);
  return slides.some((slide) => {
    const renderSchema = getRecord(slide.renderSchema ?? slide.render_schema_json);
    return Array.isArray(renderSchema.elements) && renderSchema.elements.length > 0;
  });
}

function buildSmartDeckDebug(processingVisibility: unknown, workspace: unknown): SmartDeckDebug {
  const processingSmartDeck = processingSmartDeckDebug(processingVisibility);
  const workspaceRecord = getRecord(workspace);
  const slides = workspaceGeneratedSlides(workspace);
  const sourceSlides = workspaceSourceSlides(workspace);
  const activeGeneratedSlideId = firstString(
    processingSmartDeck.activeGeneratedSlideId,
    processingSmartDeck.active_generated_slide_id,
    workspaceRecord.activeGeneratedSlideId,
    workspaceRecord.active_generated_slide_id,
    getRecord(workspaceRecord.workspace).activeGeneratedSlideId,
    slides[0]?.id
  );
  const activeSlide = activeGeneratedSlideId ? slides.find((slide) => slide.id === activeGeneratedSlideId) ?? slides[0] : slides[0];
  const renderSchema = getRecord(activeSlide?.renderSchema ?? activeSlide?.render_schema_json);
  const elementCountFromWorkspace = Array.isArray(renderSchema.elements) ? renderSchema.elements.length : 0;
  const generatedSlideCount = firstNumber(
    processingSmartDeck.generatedSlideCount,
    processingSmartDeck.generated_slide_count,
    slides.length
  ) ?? 0;
  const renderSchemaElementCount = firstNumber(
    processingSmartDeck.renderSchemaElementCount,
    processingSmartDeck.render_schema_element_count,
    elementCountFromWorkspace
  ) ?? 0;
  const hasRenderableSchema =
    processingSmartDeck.hasRenderableSchema === true ||
    workspaceHasRenderableSchema(workspace) ||
    (generatedSlideCount > 0 && renderSchemaElementCount > 0);
  const hasSourceSlides = workspaceHasSourceSlides(workspace);
  const backendReady = processingVisibility !== null ? smartDeckIsReady(processingVisibility) : null;

  return {
    processingNextAction: processingNextAction(processingVisibility),
    canOpenSmartDeck: backendReady ?? hasRenderableSchema,
    generatedSlideCount,
    sourceSlideCount: sourceSlides.length,
    activeDesignVersionId: firstString(
      processingSmartDeck.activeDesignVersionId,
      processingSmartDeck.active_design_version_id,
      workspaceRecord.activeDesignVersionId,
      workspaceRecord.active_design_version_id,
      getRecord(workspaceRecord.workspace).activeDesignVersionId
    ),
    activeGeneratedSlideId,
    renderSchemaElementCount,
    hasRenderableSchema,
    hasSourceSlides,
    workspaceStatus: firstString(processingSmartDeck.workspaceStatus, getRecord(workspaceRecord.workspace).status)
  };
}

async function loadPersistedSourceInspection(fetcher: typeof fetch, deckId: string): Promise<{
  structure: unknown;
  issues: DegradedIssue[];
}> {
  const issues: DegradedIssue[] = [];
  const workflowStateResponse = await fetchOrNull(
    fetcher,
    deckProductApiPath(`/decks/${deckId}/workflow-state`)
  );

  if (workflowStateResponse && !workflowStateResponse.ok) {
    issues.push(
      await buildIssue(
        'source-structure',
        'Source inspection',
        workflowStateResponse,
        'Could not load persisted source inspection.'
      )
    );
  }
  if (!workflowStateResponse) {
    issues.push({ key: 'source-structure', label: 'Source inspection', message: 'Could not reach source structure data.' });
  }

  const workflowState = workflowStateResponse?.ok ? await workflowStateResponse.json().catch(() => null) : null;
  const sourceSlides = Array.isArray(workflowState?.source?.slides) ? workflowState.source.slides : [];

  return {
    structure: {
      slides: sourceSlides,
      sourceEnrichment: workflowState?.source?.sourceEnrichment ?? null
    },
    issues
  };
}

async function readBackendError(response: Response, fallback: string) {
  const payload = await response.json().catch(() => null);
  return getPayloadMessage(payload, fallback);
}

function defaultWorkspacePreferences(deckId: string): DeckWorkspacePreferences {
  return {
    deckId,
    activeTool: 'deck_map',
    leftPanelOpen: true,
    selectedSlideId: null,
    lastBatchId: null,
    lastSlideVersionId: null,
    selectedElementType: null,
    selectedDataView: null,
    chatOpen: false,
    updatedAt: null
  };
}

function fallbackDeckGraph(deckId: string): DeckGraph {
  const now = new Date().toISOString();
  const slideId = `${deckId}_syncing_slide_1`;
  const blockId = `${deckId}_syncing_block_1`;

  return {
    deck: {
      id: deckId,
      workspaceId: '',
      title: 'Deck is syncing',
      audience: 'Investment Committee',
      purpose: 'Initial diligence review',
      status: 'uploaded',
      createdAt: now,
      updatedAt: now,
      summary: 'The deck metadata is temporarily unavailable while the source file and Smart Deck state sync.'
    },
    slides: [
      {
        id: slideId,
        deckId,
        slideIndex: 0,
        slideNumber: 1,
        title: 'Processing state',
        role: 'status',
        rawText: 'Smart Deck is not fully ready yet. Use the processing screen to retry or inspect the current backend state.',
        narrativeNotes: 'Fallback slide shown while Smart Deck data is degraded.',
        status: 'pending'
      }
    ],
    blocks: [
      {
        id: blockId,
        slideId,
        blockIndex: 0,
        rawText: 'Smart Deck is not fully ready yet. Use the processing screen to retry or inspect the current backend state.',
        normalizedText: 'smart deck processing fallback',
        blockType: 'body'
      }
    ],
    classifications: [],
    findings: [],
    suggestions: [],
    smartEditSuggestions: [],
    revisions: []
  };
}

function fallbackProperties(graph: DeckGraph): DeckShellProperties {
  return {
    deckId: graph.deck.id,
    companyName: null,
    companyWebsiteUrl: null,
    contactEmail: null,
    companyStage: null,
    founderName: null,
    teamSummary: null,
    brandSummary: null,
    visualDirection: null,
    audienceLabel: graph.deck.audience,
    primaryGoal: graph.deck.purpose,
    processingStatus: 'draft' as DeckShellProperties['processingStatus'],
    sourceFileName: graph.deck.originalFilename ?? null,
    brandReady: false,
    sourcesUsed: [],
    brandAssetLabels: [],
    updatedAt: null
  };
}

function fallbackWorkspaceModel(graph: DeckGraph): DeckWorkspaceModel {
  return {
    deck: {
      id: graph.deck.id,
      workspaceId: graph.deck.workspaceId,
      title: graph.deck.title,
      audience: graph.deck.audience,
      purpose: graph.deck.purpose,
      status: graph.deck.status as DeckWorkspaceModel['deck']['status'],
      summary: graph.deck.summary,
      createdAt: graph.deck.createdAt,
      updatedAt: graph.deck.updatedAt,
      generationStatus: 'idle',
      generationMode: 'mock',
      latestGenerationRunId: null
    },
    slides: graph.slides.map((slide) => ({
      id: slide.id,
      deckId: slide.deckId,
      slideNumber: slide.slideNumber ?? slide.slideIndex + 1,
      title: slide.title,
      rawText: slide.rawText,
      summary: null,
      slideRole: slide.role as DeckWorkspaceModel['slides'][number]['slideRole'],
      blocks: graph.blocks
        .filter((block) => block.slideId === slide.id)
        .map((block) => ({
          id: block.id,
          deckId: block.deckId,
          slideId: block.slideId,
          blockIndex: block.blockIndex,
          blockType: block.blockType as DeckWorkspaceModel['slides'][number]['blocks'][number]['blockType'],
          rawText: block.rawText,
          currentText: block.rawText,
          normalizedText: block.normalizedText,
          classification: null
        }))
    })),
    versions: [],
    feedback: []
  };
}

function isHardAccessFailure(response: Response | null): boolean {
  return Boolean(response && !response.ok && HARD_ACCESS_FAILURE_STATUSES.has(response.status));
}

export async function load({ params, url, fetch }) {
  if (BACKEND_URL) {
    const issues: DegradedIssue[] = [];
    const processingVisibility = await loadProcessingVisibility(fetch, params.deckId);

    if (!processingVisibility || !smartDeckIsReady(processingVisibility)) {
      throw redirect(303, `/decks/${params.deckId}/processing`);
    }

    const [
      graphResponse,
      propertiesResponse,
      preferencesResponse,
      workspaceModelResponse,
      batchesResponse,
      smartDeckWorkspaceResponse,
      providerResponse
    ] = await Promise.all([
      fetchOrNull(fetch, `/api/decks/${params.deckId}`),
      fetchOrNull(fetch, `/api/decks/${params.deckId}/properties`),
      fetchOrNull(fetch, `/api/decks/${params.deckId}/workspace`),
      fetchOrNull(fetch, deckProductApiPath(`/decks/${params.deckId}/workspace`)),
      fetchOrNull(fetch, `/api/decks/${params.deckId}/batches?limit=3`),
      fetchOrNull(fetch, `/api/decks/${params.deckId}/smart-deck`),
      fetchOrNull(fetch, '/api/settings/workspace/ai-provider')
    ]);

    if (isHardAccessFailure(graphResponse)) {
      throw error(graphResponse?.status ?? 404, graphResponse ? await readBackendError(graphResponse, 'Deck not found') : 'Deck not found');
    }

    if (graphResponse && !graphResponse.ok) {
      issues.push(await buildIssue('deck-graph', 'Deck graph', graphResponse, 'Could not load the canonical deck graph.'));
    }
    if (!graphResponse) {
      issues.push({ key: 'deck-graph', label: 'Deck graph', message: 'Could not reach the canonical deck graph.' });
    }

    if (propertiesResponse && !propertiesResponse.ok) {
      issues.push(await buildIssue('deck-properties', 'Deck properties', propertiesResponse, 'Could not load Smart Deck properties.'));
    }
    if (!propertiesResponse) {
      issues.push({ key: 'deck-properties', label: 'Deck properties', message: 'Could not reach Smart Deck properties.' });
    }

    if (preferencesResponse && !preferencesResponse.ok) {
      issues.push(await buildIssue('workspace-preferences', 'Workspace preferences', preferencesResponse, 'Could not load workspace preferences.'));
    }
    if (batchesResponse && !batchesResponse.ok) {
      issues.push(await buildIssue('design-batches', 'Design versions', batchesResponse, 'Could not load recent design versions.'));
    }
    if (!batchesResponse) {
      issues.push({ key: 'design-batches', label: 'Design versions', message: 'Could not reach recent design versions.' });
    }
    if (providerResponse && !providerResponse.ok) {
      issues.push(await buildIssue('ai-provider', 'AI provider', providerResponse, 'Could not load workspace AI provider settings.'));
    }
    if (!providerResponse) {
      issues.push({ key: 'ai-provider', label: 'AI provider', message: 'Could not reach workspace AI provider settings.' });
    }
    if (smartDeckWorkspaceResponse && !smartDeckWorkspaceResponse.ok) {
      issues.push(await buildIssue('smart-deck-workspace', 'Smart Deck workspace', smartDeckWorkspaceResponse, 'Smart Deck workspace is not ready yet.'));
    }
    if (!smartDeckWorkspaceResponse) {
      issues.push({ key: 'smart-deck-workspace', label: 'Smart Deck workspace', message: 'Could not reach the Smart Deck workspace.' });
    }

    const graph = graphResponse?.ok ? ((await graphResponse.json()) as DeckGraph) : fallbackDeckGraph(params.deckId);
    const propertiesPayload = propertiesResponse?.ok
      ? ((await propertiesResponse.json()) as { properties?: DeckShellProperties })
      : { properties: null };
    const preferencesPayload = preferencesResponse?.ok
      ? ((await preferencesResponse.json()) as { workspace?: DeckWorkspacePreferences })
      : { workspace: null };
    const workspaceModelPayload = workspaceModelResponse?.ok
      ? ((await workspaceModelResponse.json()) as {
          workspace?: DeckWorkspaceModel;
          latestConfirmation?: SaveConfirmation | null;
        })
      : { workspace: null, latestConfirmation: null };
    const batchesPayload = batchesResponse?.ok ? ((await batchesResponse.json()) as { batches?: DesignBatchPreview[] }) : { batches: [] };
    const rawSmartDeckWorkspace = smartDeckWorkspaceResponse?.ok ? ((await smartDeckWorkspaceResponse.json()) as unknown) : null;
    if (!rawSmartDeckWorkspace) {
      throw redirect(303, `/decks/${params.deckId}/processing`);
    }
    const providerPayload = providerResponse?.ok ? await providerResponse.json().catch(() => null) : null;
    const latestBatches = batchesPayload.batches ?? [];
    const activeBatchId = url.searchParams.get('batch') ?? latestBatches[0]?.id ?? null;
    const activeBatchResponse = activeBatchId
      ? await fetchOrNull(fetch, `/api/decks/${params.deckId}/batches/${activeBatchId}`)
      : null;
    if (activeBatchId && activeBatchResponse && !activeBatchResponse.ok) {
      issues.push(await buildIssue('active-batch', 'Active design version', activeBatchResponse, 'Active design version could not be loaded.'));
    }
    if (activeBatchId && !activeBatchResponse) {
      issues.push({ key: 'active-batch', label: 'Active design version', message: 'Could not reach the active design version.' });
    }
    const activeBatchPayload = activeBatchResponse?.ok
      ? ((await activeBatchResponse.json()) as { batch?: DesignBatchDetail })
      : null;
    const activeBatchError = activeBatchId && !activeBatchResponse?.ok
      ? 'Active design-version lookup failed.'
      : null;
    const sourceInspection = await loadPersistedSourceInspection(fetch, params.deckId);
    issues.push(...sourceInspection.issues);
    const workspacePreferences = preferencesPayload.workspace ?? defaultWorkspacePreferences(params.deckId);
    const properties = propertiesPayload.properties ?? fallbackProperties(graph);
    const workspaceModel = workspaceModelPayload.workspace ?? fallbackWorkspaceModel(graph);
    const smartDeckWorkspacePayload = rawSmartDeckWorkspace;
    const workspaceStatus = {
      status: 'ready' as const,
      backendStatus: smartDeckWorkspaceResponse?.status ?? 200,
      message: null,
      issues
    };
    const smartDeckDebug = buildSmartDeckDebug(processingVisibility, smartDeckWorkspacePayload);

    return {
      graph,
      properties,
      workspacePreferences,
      workspaceModel,
      latestConfirmation: workspaceModelPayload.latestConfirmation ?? null,
      latestBatches,
      activeBatch: activeBatchPayload?.batch ?? null,
      activeBatchError,
      smartDeckWorkspace: smartDeckWorkspacePayload,
      smartDeckWorkspaceStatus: workspaceStatus,
      processingVisibility,
      smartDeckProcessingVisibility: processingVisibility,
      smartDeckDebug,
      sourceInspection: {
        structure: sourceInspection.structure
      },
      aiProviderSummary: providerPayload?.summary ?? EMPTY_AI_PROVIDER_SUMMARY,
      previewDesignVersionId: url.searchParams.get('previewDesignVersionId'),
      selectedSlideId: url.searchParams.get('slide') ?? workspacePreferences.selectedSlideId ?? graph.slides[0]?.id,
      inspection: undefined
    };
  }

  const [graph, properties, workspacePreferences, workspaceModelResult, latestBatches, smartDeckWorkspaceResponse, providerResponse] = await Promise.all([
    loadDeckGraph(params.deckId).catch(() => null),
    loadDeckProperties(fetch, params.deckId),
    getDeckWorkspacePreferences(params.deckId).catch(() => defaultWorkspacePreferences(params.deckId)),
    getDeckWorkspaceModel(params.deckId).catch(() => undefined),
    listLatestDesignBatches(params.deckId, 3).catch(() => []),
    fetchOrNull(fetch, `/api/decks/${params.deckId}/smart-deck`),
    fetch('/api/settings/workspace/ai-provider').catch(() => null)
  ]);

  const localGraph = graph ?? fallbackDeckGraph(params.deckId);
  const activeBatchId = url.searchParams.get('batch') ?? latestBatches[0]?.id ?? null;
  const activeBatch = activeBatchId ? await getDesignBatchById(params.deckId, activeBatchId).catch(() => undefined) : undefined;
  const providerPayload = providerResponse?.ok ? await providerResponse.json().catch(() => null) : null;
  const sourceInspection = await loadPersistedSourceInspection(fetch, params.deckId);
  const fallbackWorkspaceModelResult = workspaceModelResult ?? {
    workspace: fallbackWorkspaceModel(localGraph),
    latestConfirmation: null
  };
  const smartDeckWorkspace = smartDeckWorkspaceResponse?.ok ? await smartDeckWorkspaceResponse.json().catch(() => null) : null;
  if (!smartDeckWorkspace) {
    throw redirect(303, `/decks/${params.deckId}/processing`);
  }

  const smartDeckDebug = buildSmartDeckDebug(null, smartDeckWorkspace);

  return {
    graph: localGraph,
    properties: properties ?? fallbackProperties(localGraph),
    workspacePreferences,
    workspaceModel: fallbackWorkspaceModelResult.workspace,
    latestConfirmation: fallbackWorkspaceModelResult.latestConfirmation,
    latestBatches,
    activeBatch: activeBatch ?? null,
    smartDeckWorkspace: smartDeckWorkspace,
    smartDeckWorkspaceStatus: { status: 'ready' as const, backendStatus: 200, message: null, issues: sourceInspection.issues },
    processingVisibility: null,
    smartDeckProcessingVisibility: null,
    smartDeckDebug,
    sourceInspection: {
      structure: sourceInspection.structure
    },
    aiProviderSummary: providerPayload?.summary ?? EMPTY_AI_PROVIDER_SUMMARY,
    previewDesignVersionId: url.searchParams.get('previewDesignVersionId'),
    selectedSlideId: url.searchParams.get('slide') ?? workspacePreferences.selectedSlideId ?? localGraph.slides[0]?.id,
    inspection: undefined
  };
}
