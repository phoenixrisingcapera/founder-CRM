import type { Cookies } from '@sveltejs/kit';
import { listLatestDesignBatches } from '$server/services/designBatchService';
import { listDeckSummaries } from '$server/services/deckService';
import { loadLatestGeneratedDeck } from '$server/services/latestGeneratedDeckService';
import { requireBackendAuthHeaders } from '$server/backendAuth';
import { requireBackendUrl } from '$server/backendApi';
import { deckProductApiPath } from '$lib/contracts';
import type { DeckSummary, FirstTimeTemplatePreview, WorkspaceAiProviderRouteResponse, WorkspaceSummary } from '@deck-aistack-codes/shared';

const EMPTY_AI_PROVIDER_SUMMARY = {
  provider: null,
  preferredModel: null,
  apiKeyLast4: null,
  isConfigured: false,
  configuredAt: null,
  skippedAt: null
} as const;

const EMPTY_FIRST_TIME_TEMPLATES: FirstTimeTemplatePreview[] = [
  {
    id: 'template_vc_diligence',
    title: 'VC diligence rewrite',
    audienceLabel: 'Investment Committee',
    description: 'Restructure an uploaded founder deck into a cleaner diligence narrative with proof gaps called out.',
    tags: ['VC', 'Diligence', 'Investment committee'],
    ctaLabel: 'Browse template'
  },
  {
    id: 'template_lp_update',
    title: 'LP or board update',
    audienceLabel: 'LP / Board',
    description: 'Turn source material into an update format that keeps the signal high and the narrative compact.',
    tags: ['Board', 'LP', 'Status update'],
    ctaLabel: 'View sample'
  },
  {
    id: 'template_advisory_version',
    title: 'Advisory review version',
    audienceLabel: 'Advisor',
    description: 'Frame the same deck for operating partners, advisers, or strategic reviewers before export.',
    tags: ['Advisory', 'Strategy', 'Review'],
    ctaLabel: 'Open preview'
  }
];

type WorkspaceAiProviderSummary = WorkspaceAiProviderRouteResponse['summary'];

function emptyWorkspaceSummary(): WorkspaceSummary {
  return {
    workspace: {
      id: 'ws_default',
      name: 'Deck AIStack Workspace'
    },
    deckCount: 0,
    activeDeckId: null,
    latestDecks: [],
    processingDeckCount: 0,
    readyDeckCount: 0,
    exportCount: 0,
    firstTimeTemplates: EMPTY_FIRST_TIME_TEMPLATES
  };
}

function toDeckSummary(deck: {
  id: string;
  title: string;
  audience: string;
  purpose: string;
  status: string;
  summary: string;
  updatedAt: string;
}): DeckSummary {
  return {
    id: deck.id,
    title: deck.title,
    audience: deck.audience as DeckSummary['audience'],
    purpose: deck.purpose,
    status: deck.status as DeckSummary['status'],
    summary: deck.summary,
    updatedAt: deck.updatedAt
  };
}

function normalizeAiProviderSummary(payload: unknown): WorkspaceAiProviderSummary {
  const record = payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : {};
  const summary = record.summary && typeof record.summary === 'object' ? (record.summary as Record<string, unknown>) : record;

  return {
    provider: typeof summary.provider === 'string' ? (summary.provider as WorkspaceAiProviderSummary['provider']) : null,
    preferredModel:
      typeof summary.preferred_model === 'string'
        ? summary.preferred_model
        : typeof summary.preferredModel === 'string'
          ? summary.preferredModel
          : null,
    apiKeyLast4:
      typeof summary.api_key_last4 === 'string'
        ? summary.api_key_last4
        : typeof summary.apiKeyLast4 === 'string'
          ? summary.apiKeyLast4
          : null,
    isConfigured: Boolean(summary.is_configured ?? summary.isConfigured ?? false),
    configuredAt:
      typeof summary.configured_at === 'string'
        ? summary.configured_at
        : typeof summary.configuredAt === 'string'
          ? summary.configuredAt
          : null,
    skippedAt:
      typeof summary.skipped_at === 'string'
        ? summary.skipped_at
        : typeof summary.skippedAt === 'string'
          ? summary.skippedAt
          : null
  };
}

async function loadPrivateWorkspacePageData(cookies: Cookies, fetcher: typeof fetch) {
  const backendUrl = requireBackendUrl();

  const [workspaceResponse, aiProviderResponse, deckSummaries] = await Promise.all([
    fetcher(`${backendUrl}${deckProductApiPath('/workspace-summary')}`, {
      headers: requireBackendAuthHeaders(cookies)
    }),
    fetcher(`${backendUrl}/api/settings/workspace/ai-provider`, {
      headers: requireBackendAuthHeaders(cookies)
    }),
    listDeckSummaries({ cookies })
  ]);

  if (!workspaceResponse.ok) {
    throw new Error('Could not load workspace summary from the backend.');
  }
  if (!aiProviderResponse.ok) {
    throw new Error('Could not load workspace AI provider from the backend.');
  }

  const workspacePayload = (await workspaceResponse.json()) as Record<string, unknown>;
  const workspaceRecord = workspacePayload.workspace as Record<string, unknown> | undefined;
  const latestDecks = (workspacePayload.latest_decks as Record<string, unknown>[] | undefined) ?? [];
  const workspace: WorkspaceSummary = {
    workspace: {
      id: String(workspaceRecord?.id ?? 'ws_default'),
      name: String(workspaceRecord?.name ?? 'Deck AIStack Workspace')
    },
    deckCount: Number(workspacePayload.deck_count ?? 0),
    activeDeckId: (workspacePayload.active_deck_id as string | null | undefined) ?? null,
    latestDecks: latestDecks.map((deck) =>
      toDeckSummary({
        id: String(deck.id ?? ''),
        title: String(deck.title ?? 'Uploaded deck'),
        audience: String(deck.audience ?? 'Investment Committee'),
        purpose: String(deck.purpose ?? 'Initial diligence review'),
        status: String(deck.status ?? 'uploaded'),
        summary: String(deck.summary ?? ''),
        updatedAt: String(deck.updated_at ?? deck.updatedAt ?? '')
      })
    ),
    processingDeckCount: Number(workspacePayload.processing_deck_count ?? 0),
    readyDeckCount: Number(workspacePayload.ready_deck_count ?? 0),
    exportCount: Number(workspacePayload.export_count ?? 0),
    firstTimeTemplates: EMPTY_FIRST_TIME_TEMPLATES
  };

  const decks: DeckSummary[] = deckSummaries.map((deck) => ({
    id: deck.id,
    title: deck.title,
    audience: deck.audience as DeckSummary['audience'],
    purpose: deck.purpose,
    status: deck.status as DeckSummary['status'],
    summary: deck.summary,
    updatedAt: deck.updatedAt
  }));
  const latestBatches = workspace.activeDeckId ? await listLatestDesignBatches(workspace.activeDeckId, 3, cookies).catch(() => []) : [];
  const normalizedWorkspace = {
    ...workspace,
    latestDecks: workspace.latestDecks.length > 0 ? workspace.latestDecks : decks,
    deckCount: Math.max(workspace.deckCount, decks.length),
    readyDeckCount: Math.max(
      workspace.readyDeckCount,
      decks.filter((deck) => deck.status === 'ready' || deck.status === 'reviewed').length
    ),
    processingDeckCount:
      workspace.processingDeckCount ||
      decks.filter((deck) =>
        ['uploaded', 'parsing', 'structuring', 'extracting_blocks', 'classifying_blocks', 'analysing', 'adapting'].includes(deck.status)
      ).length
  };

  return {
    workspace: normalizedWorkspace,
    decks,
    aiProviderSummary: normalizeAiProviderSummary(await aiProviderResponse.json()),
    latestBatches,
    inspection: null
  };
}

export async function load({ cookies, fetch }) {
  const workspace = await loadPrivateWorkspacePageData(cookies, fetch);
  const latestGeneratedDeck = await loadLatestGeneratedDeck(fetch, cookies);

  return {
    ...workspace,
    latestGeneratedDeck
  };
}
