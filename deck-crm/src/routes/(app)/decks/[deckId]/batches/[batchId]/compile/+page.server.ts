import { error, type Cookies } from '@sveltejs/kit';
import type { DesignBatchDetail, DesignBatchPreview } from '@deck-aistack-codes/shared';
import type { DeckGraph } from '$types/domain';
import type { CompiledDeckModel } from '$lib/api/finalDeck';
import { loadLatestGeneratedDeck } from '$server/services/latestGeneratedDeckService';
import { loadCompiledDeck as loadCompiledDeckById } from '$server/services/compiledDeckService';

async function loadCompiledDeckForBatch(input: {
  fetch: typeof globalThis.fetch;
  cookies: Cookies;
  deckId: string;
  batchId: string;
}): Promise<CompiledDeckModel | null> {
  const latestGeneratedDeck = await loadLatestGeneratedDeck(input.fetch, input.cookies);
  const latestMatchesRequest =
    latestGeneratedDeck?.deckId === input.deckId && latestGeneratedDeck.latestBatchId === input.batchId;
  const compiledDeckId = latestMatchesRequest ? latestGeneratedDeck.compiledDeckId ?? null : null;

  if (!compiledDeckId) {
    return null;
  }
  return loadCompiledDeckById(input.fetch, input.cookies, input.deckId, compiledDeckId);
}

export async function load({ params, fetch, cookies }: { params: { deckId: string; batchId: string }; fetch: typeof globalThis.fetch; cookies: Cookies }) {
  const graphResponse = await fetch(`/api/decks/${params.deckId}`);
  const graph = graphResponse.ok ? ((await graphResponse.json()) as DeckGraph) : null;
  if (!graph) throw error(graphResponse.status || 404, 'Deck not found');

  const batchResponse = await fetch(`/api/decks/${params.deckId}/batches/${params.batchId}`);
  if (!batchResponse.ok) throw error(batchResponse.status, 'Batch not found');
  const batchPayload = (await batchResponse.json()) as { batch?: DesignBatchDetail };
  if (!batchPayload.batch) throw error(404, 'Batch not found');

  const compiledDeck = await loadCompiledDeckForBatch({
    fetch,
    cookies,
    deckId: params.deckId,
    batchId: params.batchId
  });

  const batchesResponse = await fetch(`/api/decks/${params.deckId}/batches?limit=8`);
  if (!batchesResponse.ok) {
    throw error(batchesResponse.status, 'Could not load persisted design batches.');
  }
  const batchesPayload = (await batchesResponse.json()) as { batches?: DesignBatchPreview[] };

  return {
    graph,
    latestBatches: batchesPayload.batches ?? [],
    batch: batchPayload.batch,
    compiledDeck,
    inspection: undefined
  };
}
