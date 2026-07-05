import { error, json } from '@sveltejs/kit';
import { requireBackendAuthHeaders } from '$server/backendAuth';
import { extractErrorMessage, requireBackendUrl } from '$server/backendApi';

export async function PATCH({ params, request, fetch, cookies }) {
  const payload = await request.json();
  const backendUrl = requireBackendUrl();
  const response = await fetch(`${backendUrl}/api/decks/${params.deckId}/smart-edit/suggestions/${params.suggestionId}`, {
    method: 'PATCH',
    headers: { ...requireBackendAuthHeaders(cookies), 'content-type': 'application/json' },
    body: JSON.stringify({
      status: payload.status,
      edited_text: payload.edited_text ?? payload.finalText ?? null
    })
  });
  const result = await response.json().catch(() => null);
  if (!response.ok) {
    throw error(response.status, extractErrorMessage(result, 'Smart Edit suggestion update failed.'));
  }
  return json(result, { status: response.status });
}
