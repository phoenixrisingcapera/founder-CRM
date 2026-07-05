import { error } from '@sveltejs/kit';
import type { DesignBatchPreview } from '@deck-aistack-codes/shared';
import type { DeckGraph } from '$types/domain';

export async function load({ params, fetch }) {
  const graphResponse = await fetch(`/api/decks/${params.deckId}`);
  const graph = graphResponse.ok ? ((await graphResponse.json()) as DeckGraph) : null;
  if (!graph) throw error(graphResponse.status || 404, 'Deck not found');

  const batchesResponse = await fetch(`/api/decks/${params.deckId}/batches?limit=50`);
  if (!batchesResponse.ok) throw error(batchesResponse.status, 'Could not load deck batches.');
  const batchesPayload = (await batchesResponse.json()) as { batches?: DesignBatchPreview[] };
  const batches = batchesPayload.batches ?? [];

  return {
    graph,
    latestBatches: batches.slice(0, 8),
    batches,
    inspection: undefined
  };
}
