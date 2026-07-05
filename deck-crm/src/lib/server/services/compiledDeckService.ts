import type { Cookies } from '@sveltejs/kit';
import { error } from '@sveltejs/kit';
import { requireBackendAuthHeaders } from '$server/backendAuth';
import { requireBackendUrl } from '$server/backendApi';
import type { CompiledDeckModel } from '$lib/api/finalDeck';

export async function loadCompiledDeck(
  fetcher: typeof globalThis.fetch,
  cookies: Cookies,
  deckId: string,
  compiledDeckId: string
): Promise<CompiledDeckModel | null> {
  const backendUrl = requireBackendUrl();
  const response = await fetcher(`${backendUrl}/api/decks/${deckId}/compiled-decks/${compiledDeckId}`, {
    headers: requireBackendAuthHeaders(cookies)
  }).catch(() => null);

  if (!response) {
    throw error(503, 'Compiled deck lookup failed.');
  }
  if (!response.ok) {
    if (response.status === 404) {
      return null;
    }
    throw error(response.status, 'Compiled deck lookup failed.');
  }

  const payload = await response.json().catch(() => null);
  return payload?.compiledDeck ?? null;
}
