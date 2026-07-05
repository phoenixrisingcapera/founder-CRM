import { error, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import { loadAdminDeckProcessing } from '$server/adminApi';

export async function load({ cookies, fetch, params, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  try {
    return {
      processing: await loadAdminDeckProcessing(fetch, cookies, params.deckId)
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'Admin deck processing state is unavailable.');
  }
}
