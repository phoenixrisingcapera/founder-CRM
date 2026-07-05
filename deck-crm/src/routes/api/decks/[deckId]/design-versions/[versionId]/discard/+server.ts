import { proxyBackendJson } from '$server/backendApi';

export async function POST({ params, fetch, cookies }) {
  return proxyBackendJson(
    fetch,
    cookies,
    `/api/decks/${params.deckId}/design-versions/${params.versionId}/discard`,
    { method: 'POST' },
    'Design version discard failed.'
  );
}
