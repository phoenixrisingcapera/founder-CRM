import type { WorkspaceSummary } from '@deck-aistack-codes/shared';
import { deckProductApiPath } from '$lib/contracts';

const EMPTY_AI_PROVIDER_SUMMARY = {
  provider: null,
  preferredModel: null,
  apiKeyLast4: null,
  isConfigured: false,
  configuredAt: null,
  skippedAt: null
} as const;

const TESTER_EMPTY_WORKSPACE = {
  workspace: { id: 'ws_tester_entry', name: 'Deck AIStack Workspace' },
  deckCount: 0,
  activeDeckId: null,
  latestDecks: [],
  processingDeckCount: 0,
  readyDeckCount: 0,
  exportCount: 0,
  firstTimeTemplates: []
} satisfies WorkspaceSummary;

const FALLBACK_MESSAGE =
  'We could not load your previous decks right now. You can still upload a new deck and continue testing.';

async function readJsonResponse(response: Response) {
  return response.json().catch(() => null);
}

function workspaceFallback(status: number, message: string, locals: App.Locals, routeNotice: string | null) {
  return {
    workspace: TESTER_EMPTY_WORKSPACE,
    decks: [],
    aiProviderSummary: EMPTY_AI_PROVIDER_SUMMARY,
    latestBatches: [],
    inspection: locals.founderInspection,
    routeNotice,
    workspaceLoadStatus: {
      status: 'degraded' as const,
      backendStatus: status,
      message
    }
  };
}

export async function load({ fetch, locals, url }) {
  const routeNotice = url.searchParams.get('notice') === 'admin-internal' ? 'admin-internal' : null;
  const [workspaceResult, providerResult] = await Promise.allSettled([
    fetch(deckProductApiPath('/workspace-summary')),
    fetch('/api/settings/workspace/ai-provider')
  ]);

  if (workspaceResult.status === 'rejected') {
    console.error('[welcome] workspace summary request rejected before reaching backend');
    return workspaceFallback(503, FALLBACK_MESSAGE, locals, routeNotice);
  }

  const workspaceResponse = workspaceResult.value;
  if (!workspaceResponse.ok) {
    const payload = await readJsonResponse(workspaceResponse);
    console.error('[welcome] workspace summary request failed', {
      status: workspaceResponse.status,
      hasPayload: Boolean(payload)
    });
    return workspaceFallback(workspaceResponse.status, FALLBACK_MESSAGE, locals, routeNotice);
  }

  const workspacePayload = (await workspaceResponse.json()) as { workspace: WorkspaceSummary };
  const providerResponse = providerResult.status === 'fulfilled' ? providerResult.value : null;
  const providerPayload = providerResponse?.ok
    ? await providerResponse.json()
    : { summary: EMPTY_AI_PROVIDER_SUMMARY };
  const data = {
    workspace: workspacePayload.workspace,
    decks: workspacePayload.workspace.latestDecks ?? [],
    aiProviderSummary: providerPayload.summary ?? EMPTY_AI_PROVIDER_SUMMARY,
    latestBatches: [],
    inspection: locals.founderInspection,
    routeNotice,
    workspaceLoadStatus: {
      status: 'ready' as const,
      backendStatus: workspaceResponse.status,
      message: null
    }
  };

  return data;
}
