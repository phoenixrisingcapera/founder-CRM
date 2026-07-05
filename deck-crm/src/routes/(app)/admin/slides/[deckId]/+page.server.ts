import { error, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import { loadAdminDeckSlides } from '$server/adminApi';

export async function load({ cookies, fetch, params, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  try {
    return {
      slides: await loadAdminDeckSlides(fetch, cookies, params.deckId)
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'Admin slide inspection is unavailable.');
  }
}
