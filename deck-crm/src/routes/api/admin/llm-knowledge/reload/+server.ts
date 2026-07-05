import { proxyBackendJson, requireBackendUrl } from '$server/backendApi';

export async function POST({ fetch, cookies, request }) {
  requireBackendUrl();
  return proxyBackendJson(
    fetch,
    cookies,
    '/api/admin/llm-knowledge/reload',
    { method: 'POST', body: await request.text() },
    'Could not reload LLM knowledge.'
  );
}
