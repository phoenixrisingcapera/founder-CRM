import { proxyBackendJson } from '$server/backendApi';

export async function GET({ params, fetch, cookies }) {
  return proxyBackendJson(
    fetch,
    cookies,
    `/api/decks/${params.deckId}/generated-slides/${params.generatedSlideId}/code`,
    { method: 'GET' },
    'Generated slide code lookup failed.'
  );
}
