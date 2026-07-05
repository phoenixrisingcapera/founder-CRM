import { error, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import { loadAdminFailureTickets } from '$server/adminApi';

export async function load({ cookies, fetch, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  const limit = Number(url.searchParams.get('limit') ?? 100);

  try {
    return {
      failureTickets: await loadAdminFailureTickets(fetch, cookies, {
        limit: Number.isFinite(limit) ? limit : 100,
        status: url.searchParams.get('status'),
        severity: url.searchParams.get('severity'),
        source: url.searchParams.get('source'),
        deckId: url.searchParams.get('deckId')
      })
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'Failure tickets are unavailable.');
  }
}
