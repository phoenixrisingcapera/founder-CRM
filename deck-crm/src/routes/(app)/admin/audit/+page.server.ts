import { error, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import { loadAdminAudit } from '$server/adminApi';

export async function load({ cookies, fetch, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  const limit = Number(url.searchParams.get('limit') ?? 100);

  try {
    return {
      audit: await loadAdminAudit(fetch, cookies, {
        limit: Number.isFinite(limit) ? limit : 100,
        action: url.searchParams.get('action'),
        result: url.searchParams.get('result'),
        resourceType: url.searchParams.get('resourceType'),
        actor: url.searchParams.get('actor')
      })
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'Admin audit feed is unavailable.');
  }
}
