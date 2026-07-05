import { error, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import { loadAdminOverview } from '$server/adminApi';

export async function load({ cookies, fetch, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  try {
    return {
      overview: await loadAdminOverview(fetch, cookies)
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'Admin overview is unavailable.');
  }
}
