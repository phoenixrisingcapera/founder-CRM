import { error } from '@sveltejs/kit';
import type { DesignBatchPreview } from '@deck-aistack-codes/shared';
import type { DeckGraph } from '$types/domain';

export async function load({ params, fetch }) {
  const graphResponse = await fetch(`/api/decks/${params.deckId}`);
  const graph = graphResponse.ok ? ((await graphResponse.json()) as DeckGraph) : null;
  if (!graph) throw error(graphResponse.status || 404, 'Deck not found');

  const batchesResponse = await fetch(`/api/decks/${params.deckId}/batches?limit=8`);
  const batchesPayload = batchesResponse.ok
    ? ((await batchesResponse.json()) as { batches?: DesignBatchPreview[] })
    : { batches: [] };

  return {
    graph,
    latestBatches: batchesPayload.batches ?? [],
    inspection: undefined
  };
}
