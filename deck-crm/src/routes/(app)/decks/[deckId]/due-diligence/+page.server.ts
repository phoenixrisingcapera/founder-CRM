import { error } from '@sveltejs/kit';
import { deckProductApiPath } from '$lib/contracts';
import type { DeckGraph } from '$types/domain';

async function readBackendError(response: Response, fallback: string) {
  const payload = await response.json().catch(() => null);
  if (payload && typeof payload === 'object') {
    const record = payload as Record<string, unknown>;
    if (typeof record.detail === 'string') return record.detail;
    if (typeof record.message === 'string') return record.message;
    if (typeof record.error === 'string') return record.error;
  }
  return fallback;
}

function degradedDiligenceWorkspace(deckId: string, audience: string | null, message: string, backendStatus?: number) {
  return {
    ok: false,
    deckId,
    status: 'unavailable',
    backendStatus: backendStatus ?? null,
    selectedAudience: audience,
    message,
    findings: [],
    checklist: [],
    nextAction: 'retry_later'
  };
}

type PageLoad = {
  params: { deckId: string };
  fetch: typeof fetch;
  url: URL;
};

export async function load({ params, fetch, url }: PageLoad) {
  const audience = url.searchParams.get('audience');
  const [graphResponse, workspaceResponse, batchesResponse] = await Promise.all([
    fetch(`/api/decks/${params.deckId}`),
    fetch(deckProductApiPath(`/decks/${params.deckId}/due-diligence${audience ? `?audience=${encodeURIComponent(audience)}` : ''}`)).catch(
      () => null
    ),
    fetch(`/api/decks/${params.deckId}/batches?limit=8`).catch(() => null)
  ]);

  const graph = graphResponse.ok ? ((await graphResponse.json()) as DeckGraph) : null;
  if (!graph) throw error(graphResponse.status || 404, 'Deck not found');

  const latestBatches = batchesResponse?.ok ? ((await batchesResponse.json()) as { batches?: unknown[] }).batches ?? [] : [];
  const diligenceWorkspace = workspaceResponse?.ok
    ? await workspaceResponse.json().catch(() => degradedDiligenceWorkspace(params.deckId, audience, 'Could not parse diligence workspace.'))
    : degradedDiligenceWorkspace(
        params.deckId,
        audience,
        workspaceResponse ? await readBackendError(workspaceResponse, 'Due diligence is not ready for this deck yet.') : 'Due diligence is temporarily unavailable.',
        workspaceResponse?.status
      );

  return {
    graph,
    latestBatches,
    diligenceWorkspace,
    selectedAudience: audience ?? null
  };
}
