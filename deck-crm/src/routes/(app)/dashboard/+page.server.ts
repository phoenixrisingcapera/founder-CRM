import { error, isHttpError, isRedirect, redirect } from '@sveltejs/kit';
import type { Cookies } from '@sveltejs/kit';
import { getBackendAccessToken, requireBackendAuthHeaders } from '$server/backendAuth';
import { requireBackendUrl } from '$server/backendApi';
import type { WorkspaceDashboardResponse } from '$lib/types/workspace-dashboard';
import type { Deck } from '$types/domain';
import type { DeckSummary, WorkspaceAiProviderRouteResponse, WorkspaceSummary } from '@deck-aistack-codes/shared';

const EMPTY_AI_PROVIDER_SUMMARY = {
  provider: null,
  preferredModel: null,
  apiKeyLast4: null,
  isConfigured: false,
  configuredAt: null,
  skippedAt: null
} as const;

type WorkspaceAiProviderSummary = WorkspaceAiProviderRouteResponse['summary'];

function deckSummaryStatus(status: string): DeckSummary['status'] {
  if (status === 'preparing') return 'uploaded';
  if (status === 'ready_to_review') return 'ready';
  if (status === 'exported') return 'reviewed';
  return status as DeckSummary['status'];
}

function domainDeckStatus(status: string): Deck['status'] {
  if (status === 'preparing') return 'uploaded';
  if (status === 'ready_to_review') return 'ready';
  if (status === 'exported') return 'reviewed';
  return status as Deck['status'];
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

async function loadBackendAiProviderSummary(fetcher: typeof fetch, cookies: Cookies, nextPath: string) {
  const backendUrl = requireBackendUrl();
  const response = await fetcher(`${backendUrl}/api/settings/workspace/ai-provider`, {
    headers: requireBackendAuthHeaders(cookies)
  });

  if (response.status === 401 || response.status === 403) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(nextPath)}`);
  }
  if (!response.ok) {
    const message = await response.text().catch(() => 'Workspace AI provider request failed.');
    logDashboardLoadFailure('ai_provider_response_not_ok', message, { status: response.status });
    throw error(response.status, 'Workspace AI provider request failed.');
  }

  return normalizeAiProviderSummary(await response.json());
}

function pageDataFromDashboard(
  dashboard: WorkspaceDashboardResponse,
  inspection: App.Locals['founderInspection'],
  aiProviderSummary: WorkspaceAiProviderSummary = EMPTY_AI_PROVIDER_SUMMARY
) {
  const latestDecks: DeckSummary[] = dashboard.decks.slice(0, 3).map((deck) => ({
    id: deck.id,
    title: deck.title,
    audience: deck.audience as DeckSummary['audience'],
    purpose: deck.purpose,
    status: deckSummaryStatus(deck.status),
    summary: deck.description,
    updatedAt: deck.updatedAt
  }));
  const workspace: WorkspaceSummary = {
    workspace: {
      id: 'ws_backend',
      name: 'Deck AIStack Workspace'
    },
    deckCount: dashboard.stats.uploadedDecks,
    activeDeckId: dashboard.latestDeck?.id ?? dashboard.decks[0]?.id ?? null,
    latestDecks,
    processingDeckCount: dashboard.decks.filter((deck) => deck.status === 'preparing').length,
    readyDeckCount: dashboard.decks.filter((deck) => ['ready_to_review', 'reviewed'].includes(deck.status)).length,
    exportCount: dashboard.decks.filter((deck) => deck.status === 'exported').length,
    firstTimeTemplates: []
  };
  const decks: Deck[] = dashboard.decks.map((deck) => ({
    id: deck.id,
    workspaceId: workspace.workspace.id,
    title: deck.title,
    audience: deck.audience,
    purpose: deck.purpose,
    status: domainDeckStatus(deck.status),
    summary: deck.description,
    createdAt: deck.updatedAt,
    updatedAt: deck.updatedAt
  }));

  return {
    workspace,
    decks,
    aiProviderSummary,
    latestBatches: [],
    inspection
  };
}

function logDashboardLoadFailure(reason: string, error: unknown, details: Record<string, unknown> = {}) {
  console.error('Dashboard load failed', {
    reason,
    ...details,
    error: error instanceof Error ? error.message : String(error)
  });
}

export async function load({ cookies, fetch, locals, url }) {
  const backendUrl = requireBackendUrl();
  const nextPath = `${url.pathname}${url.search}`;
  const token = getBackendAccessToken(cookies);
  if (!token) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(nextPath)}`);
  }

  try {
    const [response, aiProviderSummary] = await Promise.all([
      fetch(`${backendUrl}/api/workspace/dashboard`, {
        headers: requireBackendAuthHeaders(cookies)
      }),
      loadBackendAiProviderSummary(fetch, cookies, nextPath)
    ]);

    if (response.status === 401 || response.status === 403) {
      throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(nextPath)}`);
    }

    if (!response.ok) {
      const message = await response.text().catch(() => 'Backend dashboard request failed.');
      logDashboardLoadFailure('backend_response_not_ok', message, { status: response.status });
      throw error(response.status, 'Workspace dashboard backend request failed.');
    }

    const dashboard = (await response.json()) as WorkspaceDashboardResponse;
    return {
      ...pageDataFromDashboard(dashboard, locals.founderInspection, aiProviderSummary),
      dashboard
    };
  } catch (err) {
    if (isRedirect(err)) {
      throw err;
    }
    if (isHttpError(err)) {
      throw err;
    }

    logDashboardLoadFailure('backend_fetch_failed', err, { backendConfigured: true });
    throw error(503, 'Workspace dashboard backend is unavailable.');
  }
}
