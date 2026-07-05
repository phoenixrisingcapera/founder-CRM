import { error, json } from '@sveltejs/kit';
import { requireBackendAuthHeaders } from '$server/backendAuth';
import { extractErrorMessage, requireBackendUrl } from '$server/backendApi';

export async function GET({ params, fetch, cookies }) {
  const backendUrl = requireBackendUrl();
  const response = await fetch(`${backendUrl}/api/assistant/runs/${params.runId}`, {
    headers: requireBackendAuthHeaders(cookies)
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw error(response.status, extractErrorMessage(payload, 'Assistant run lookup failed.'));
  }
  return json(payload, { status: response.status });
}
