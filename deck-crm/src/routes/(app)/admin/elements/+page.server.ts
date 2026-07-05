import { error, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import { loadAdminElements } from '$server/adminApi';

export async function load({ cookies, fetch, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  const limit = Number(url.searchParams.get('limit') ?? 100);
  const deckId = url.searchParams.get('deckId');

  try {
    return {
      elements: await loadAdminElements(fetch, cookies, {
        deckId,
        limit: Number.isFinite(limit) ? limit : 100
      })
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'Admin element inspection is unavailable.');
  }
}
