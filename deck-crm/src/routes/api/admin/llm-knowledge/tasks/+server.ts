import { proxyBackendJson, requireBackendUrl } from '$server/backendApi';

export async function GET({ fetch, cookies }) {
  requireBackendUrl();
  return proxyBackendJson(fetch, cookies, '/api/admin/llm-knowledge/tasks', {}, 'Could not load LLM knowledge task contracts.');
}
