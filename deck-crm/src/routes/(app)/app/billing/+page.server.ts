import { error } from '@sveltejs/kit';

export async function load({ fetch, locals }) {
  const response = await fetch('/api/billing');
  const payload = await response.json().catch(() => null);

  if (!response.ok || !payload?.billing) {
    throw error(response.status || 503, payload?.message ?? 'Could not load billing from the backend.');
  }

  return {
    billing: payload.billing,
    inspection: locals.founderInspection
  };
}
