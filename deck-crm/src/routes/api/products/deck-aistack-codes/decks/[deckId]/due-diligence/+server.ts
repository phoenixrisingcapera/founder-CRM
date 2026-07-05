import { type RequestHandler } from '@sveltejs/kit';
import { deckProductApiPath } from '$lib/contracts';
import { proxyBackendJson } from '$server/backendApi';

export const GET: RequestHandler = async ({ params, url, fetch, cookies }) => {
  const audience = url.searchParams.get('audience');
  const audienceSuffix = audience ? `?audience=${encodeURIComponent(audience)}` : '';

  return proxyBackendJson(
    fetch,
    cookies,
    deckProductApiPath(`/decks/${params.deckId}/due-diligence${audienceSuffix}`),
    {},
    'Due diligence workspace not found.'
  );
};

export const POST: RequestHandler = async ({ params, request, fetch, cookies }) => {
  const payload = await request.json().catch(() => ({}));
  return proxyBackendJson(
    fetch,
    cookies,
    deckProductApiPath(`/decks/${params.deckId}/due-diligence/run`),
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify(payload)
    },
    'Failed to run due diligence review.'
  );
};
