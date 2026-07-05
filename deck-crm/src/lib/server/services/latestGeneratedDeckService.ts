import type { Cookies } from '@sveltejs/kit';
import { requireBackendAuthHeaders } from '$server/backendAuth';
import { requireBackendUrl } from '$server/backendApi';
import type { LatestGeneratedDeckCardModel } from '$lib/api/finalDeck';

export async function loadLatestGeneratedDeck(
  fetcher: typeof globalThis.fetch,
  cookies: Cookies
): Promise<LatestGeneratedDeckCardModel | null> {
  const backendUrl = requireBackendUrl();
  const response = await fetcher(`${backendUrl}/api/decks/generated/latest`, {
    headers: requireBackendAuthHeaders(cookies)
  }).catch(() => null);
  if (!response?.ok) return null;
  const payload = await response.json().catch(() => null);
  return payload?.latestGeneratedDeck ?? null;
}
