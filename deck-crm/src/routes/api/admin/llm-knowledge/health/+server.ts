import { proxyBackendJson, requireBackendUrl } from '$server/backendApi';

export async function GET({ fetch, cookies }) {
  requireBackendUrl();
  return proxyBackendJson(fetch, cookies, '/api/admin/llm-knowledge/health', {}, 'Could not load LLM knowledge health.');
}
