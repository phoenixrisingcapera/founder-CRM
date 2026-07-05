import { error } from '@sveltejs/kit';

export async function load({ fetch, locals }) {
  const response = await fetch('/api/settings/account/connected-accounts');
  const payload = await response.json().catch(() => null);

  if (!response.ok || !payload?.settings) {
    throw error(response.status || 503, payload?.message ?? 'Could not load connected accounts from the backend.');
  }

  return { settings: payload.settings, inspection: locals.founderInspection };
}
