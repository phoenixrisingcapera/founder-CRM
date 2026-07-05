import { error } from '@sveltejs/kit';
import { proxyBackendJson } from '$server/backendApi';

export async function POST({ request, fetch, cookies }) {
  const payload = (await request.json().catch(() => null)) as {
    deckId?: string;
    intentType?: string;
    scope?: 'current_slide' | 'selected_slides' | 'whole_deck';
    currentSlideId?: string | null;
    selectedSlideIds?: string[];
    instruction?: string;
    audience?: string | null;
  } | null;

  if (!payload?.deckId) {
    throw error(400, 'deckId is required.');
  }
  if (!payload.intentType) {
    throw error(400, 'intentType is required.');
  }

  const selectedSourceSlideIds =
    payload.scope === 'selected_slides'
      ? (payload.selectedSlideIds ?? [])
      : payload.scope === 'current_slide' && payload.currentSlideId
        ? [payload.currentSlideId]
        : [];

  return proxyBackendJson(
    fetch,
    cookies,
    '/api/assistant/runs',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        deckId: payload.deckId,
        intentType: payload.intentType,
        scope: payload.scope ?? 'whole_deck',
        currentSlideId: payload.currentSlideId ?? null,
        selectedSlideIds: selectedSourceSlideIds,
        instruction: payload.instruction ?? '',
        audience: payload.audience ?? null
      })
    },
    'Assistant run failed.'
  );
}
