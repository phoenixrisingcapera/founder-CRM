import { error, json } from '@sveltejs/kit';
import { extractErrorMessage, parseJson, requireBackendUrl } from '$server/backendApi';
import { requireBackendAuthHeaders } from '$server/backendAuth';

export async function PATCH({ params, request, fetch, cookies }) {
  const payload = await request.json().catch(() => ({}));
  const choice = String(payload?.choice ?? '');
  const backendUrl = requireBackendUrl();

  const path =
    choice === 'generated_version'
      ? `/api/products/dididecks/slides/${params.slideId}/accept-version`
      : choice === 'original'
        ? `/api/products/dididecks/slides/${params.slideId}/keep-original`
        : null;

  if (!path) {
    throw error(400, 'choice must be generated_version or original.');
  }

  const response = await fetch(`${backendUrl}${path}`, {
    method: 'POST',
    headers: {
      ...requireBackendAuthHeaders(cookies),
      'content-type': 'application/json'
    },
    body: JSON.stringify({
      deckId: params.deckId,
      batchId: params.batchId,
      generatedVersionId: payload?.generatedSlideVersionId ?? null,
      generatedSlideVersionId: payload?.generatedSlideVersionId ?? null
    })
  });
  const result = await parseJson(response);

  if (!response.ok) {
    throw error(response.status, extractErrorMessage(result, 'Could not save slide decision.'));
  }

  return json(
    {
      ...result,
      candidateStatus: choice === 'generated_version' ? 'accepted' : 'rejected'
    },
    { status: response.status }
  );
}
