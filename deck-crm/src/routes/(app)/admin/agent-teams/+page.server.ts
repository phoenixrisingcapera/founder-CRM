import { error, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import { loadAdminAgentTeams } from '$server/adminApi';

export async function load({ cookies, fetch, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  try {
    return {
      agentTeams: await loadAdminAgentTeams(fetch, cookies)
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'Admin agent teams are unavailable.');
  }
}
