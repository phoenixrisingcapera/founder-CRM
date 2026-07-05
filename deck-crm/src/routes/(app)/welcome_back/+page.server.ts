import type { DeckShellProperties, DeckSummary, DesignBatchPreview, WorkspaceSummary } from '@deck-aistack-codes/shared';
import { deckProductApiPath } from '$lib/contracts';
import type { DeckGraph } from '$types/domain';

const EMPTY_AI_PROVIDER_SUMMARY = {
  provider: null,
  preferredModel: null,
  apiKeyLast4: null,
  isConfigured: false,
  configuredAt: null,
  skippedAt: null
} as const;

const EMPTY_WORKSPACE = {
  workspace: { id: 'ws_empty', name: 'Deck AIStack Workspace' },
  deckCount: 0,
  activeDeckId: null,
  latestDecks: [],
  processingDeckCount: 0,
  readyDeckCount: 0,
  exportCount: 0,
  firstTimeTemplates: []
} satisfies WorkspaceSummary;

async function readJson<T>(response: Response | null): Promise<T | null> {
  if (!response?.ok) return null;
  return response.json().catch(() => null);
}

function degradedReason(response: Response | null, fallback: string) {
  if (!response) return fallback;
  return `${fallback} Backend status ${response.status}.`;
}

export async function load({ fetch, locals }) {
  const [workspaceResult, welcomeStateResult, providerResult] = await Promise.allSettled([
    fetch(deckProductApiPath('/workspace-summary')).catch(() => null),
    fetch(deckProductApiPath('/welcome-state')).catch(() => null),
    fetch('/api/settings/workspace/ai-provider').catch(() => null)
  ]);

  const workspaceResponse = workspaceResult.status === 'fulfilled' ? workspaceResult.value : null;
  const welcomeStateResponse = welcomeStateResult.status === 'fulfilled' ? welcomeStateResult.value : null;
  const providerResponse = providerResult.status === 'fulfilled' ? providerResult.value : null;
  const workspacePayload = await readJson<{ workspace: WorkspaceSummary }>(workspaceResponse);
  const workspace = workspacePayload?.workspace ?? EMPTY_WORKSPACE;
  const workspaceLoadStatus = workspacePayload?.workspace
    ? { status: 'ready' as const, message: null as string | null }
    : { status: 'degraded' as const, message: degradedReason(workspaceResponse, 'Could not load persisted workspace summary.') };

  if (workspace.deckCount === 0) {
    return {
      workspace,
      decks: [] as DeckSummary[],
      aiProviderSummary: EMPTY_AI_PROVIDER_SUMMARY,
      latestBatches: [] as DesignBatchPreview[],
      inspection: locals.founderInspection,
      welcomeState: null,
      primaryDeckGraph: null,
      primaryDeckProperties: null,
      workspaceLoadStatus
    };
  }

  const welcomeState = await readJson<Record<string, any>>(welcomeStateResponse);
  const providerPayload = await readJson<{ summary?: typeof EMPTY_AI_PROVIDER_SUMMARY }>(providerResponse);
  const workspaceData = {
    workspace,
    decks: (workspace.latestDecks ?? []) as DeckSummary[],
    aiProviderSummary: providerPayload?.summary ?? EMPTY_AI_PROVIDER_SUMMARY,
    latestBatches: [] as DesignBatchPreview[],
    inspection: locals.founderInspection,
    welcomeState,
    workspaceLoadStatus
  };

  const primaryDeckId =
    welcomeState?.resumeCard?.deckId ??
    workspaceData.workspace.activeDeckId ??
    workspaceData.decks[0]?.id ??
    null;

  if (!primaryDeckId) {
    return {
      ...workspaceData,
      primaryDeckGraph: null,
      primaryDeckProperties: null
    };
  }

  const [graphResponse, propertiesResponse, batchesResponse] = await Promise.all([
    fetch(`/api/decks/${primaryDeckId}`).catch(() => null),
    fetch(`/api/decks/${primaryDeckId}/properties`).catch(() => null),
    fetch(`/api/decks/${primaryDeckId}/batches?limit=3`).catch(() => null)
  ]);

  const primaryDeckGraph =
    graphResponse?.ok ? ((await graphResponse.json()) as DeckGraph) : null;
  const propertiesPayload =
    propertiesResponse?.ok ? ((await propertiesResponse.json()) as { properties?: DeckShellProperties }) : null;
  const batchesPayload =
    batchesResponse?.ok ? ((await batchesResponse.json()) as { batches?: DesignBatchPreview[] }) : null;

  return {
    ...workspaceData,
    latestBatches: batchesPayload?.batches ?? [],
    primaryDeckGraph,
    primaryDeckProperties: propertiesPayload?.properties ?? null
  };
}
