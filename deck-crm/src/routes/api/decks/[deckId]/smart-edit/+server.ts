import { error, json } from '@sveltejs/kit';
import { requireBackendAuthHeaders } from '$server/backendAuth';
import { extractErrorMessage, requireBackendUrl } from '$server/backendApi';

export async function POST({ params, request, fetch, cookies }) {
  const payload = await request.json();
  const backendUrl = requireBackendUrl();
  const response = await fetch(`${backendUrl}/api/decks/${params.deckId}/smart-edit`, {
    method: 'POST',
    headers: { ...requireBackendAuthHeaders(cookies), 'content-type': 'application/json' },
    body: JSON.stringify({
      slide_id: payload.slide_id ?? payload.slideId,
      block_id: payload.block_id ?? payload.blockId,
      instruction: payload.instruction,
      audience_type: payload.audience_type ?? payload.audienceType
    })
  });
  const result = await response.json().catch(() => null);
  if (!response.ok) {
    throw error(response.status, extractErrorMessage(result, 'Smart Edit failed.'));
  }
  return json(result, { status: response.status });
}
