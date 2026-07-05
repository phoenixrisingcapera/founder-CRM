import { error } from '@sveltejs/kit';
import { deckProductApiPath } from '$lib/contracts';
import type { DesignBatchPreview } from '@deck-aistack-codes/shared';
import type { DeckGraph } from '$types/domain';

export async function load({ params, url, fetch }) {
  const graphResponse = await fetch(`/api/decks/${params.deckId}`);
  const graph = graphResponse.ok ? ((await graphResponse.json()) as DeckGraph) : null;
  if (!graph) throw error(graphResponse.status || 404, 'Deck not found');

  const selectedSlideId = url.searchParams.get('slide') ?? graph.slides[0]?.id;
  const selectedBlockId =
    url.searchParams.get('block') ??
    graph.blocks.find((block) => block.slideId === selectedSlideId)?.id ??
    undefined;

  const batchesResponse = await fetch(`/api/decks/${params.deckId}/batches?limit=8`);
  const fieldsResponse = await fetch(deckProductApiPath(`/decks/${params.deckId}/editable-fields`));
  if (!batchesResponse.ok) {
    throw error(batchesResponse.status, 'Could not load persisted design batches.');
  }
  if (!fieldsResponse.ok) {
    throw error(fieldsResponse.status, 'Could not load editable fields.');
  }
  const batchesPayload = (await batchesResponse.json()) as { batches?: DesignBatchPreview[] };
  const fieldsPayload = (await fieldsResponse.json()) as { fields?: Array<{ fieldKey: string }> };

  const selectedFieldKey = selectedBlockId ? `block:${selectedBlockId}.raw_text` : selectedSlideId ? `slide:${selectedSlideId}.title` : 'deck.title';
  const selectedFieldResponse = await fetch(deckProductApiPath(`/decks/${params.deckId}/fields/${selectedFieldKey}`));
  const selectedField = selectedFieldResponse.ok ? await selectedFieldResponse.json() : null;

  return {
    graph,
    latestBatches: batchesPayload.batches ?? [],
    selectedSlideId,
    selectedBlockId,
    selectedFieldKey,
    editableFields: fieldsPayload.fields ?? [],
    selectedField,
    initialInstruction: url.searchParams.get('instruction') ?? null,
    assistantRunId: url.searchParams.get('assistantRunId') ?? null,
    inspection: undefined
  };
}
