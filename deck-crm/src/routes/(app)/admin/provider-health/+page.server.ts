import { error, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import { loadAdminProviderHealth } from '$server/adminApi';

export async function load({ cookies, fetch, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  const limit = Number(url.searchParams.get('limit') ?? 100);

  try {
    return {
      providerHealth: await loadAdminProviderHealth(fetch, cookies, Number.isFinite(limit) ? limit : 100)
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'Admin provider health is unavailable.');
  }
}
