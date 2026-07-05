import { error, json, type Cookies } from '@sveltejs/kit';
import { randomUUID } from 'node:crypto';
import { requireBackendAuthHeaders } from '$server/backendAuth';
import { reportFailureTicketToBackend } from '$server/failureTickets';
import { BACKEND_URL, BACKEND_URL_ENV_NAME } from '$server/backendUrl';

export { BACKEND_URL } from '$server/backendUrl';

export function requireBackendUrl() {
  if (!BACKEND_URL) {
    throw error(503, `Backend URL is required. Set ${BACKEND_URL_ENV_NAME}.`);
  }

  return BACKEND_URL;
}

export function extractErrorMessage(payload: unknown, fallback = 'Request failed.') {
  if (!payload || typeof payload !== 'object') return fallback;
  const record = payload as Record<string, unknown>;

  if (typeof record.message === 'string') return record.message;
  if (typeof record.detail === 'string') return record.detail;
  if (record.detail && typeof record.detail === 'object') {
    const detail = record.detail as Record<string, unknown>;
    if (typeof detail.message === 'string') return detail.message;
    if (typeof detail.error === 'string') return detail.error;
  }
  if (typeof record.error === 'string') return record.error;

  return fallback;
}

export async function parseJson(response: Response) {
  return response.json().catch(() => null);
}

export async function proxyBackendJson(
  fetcher: typeof fetch,
  cookies: Cookies,
  path: string,
  init: RequestInit = {},
  fallbackMessage = 'Backend request failed.'
) {
  const backendUrl = requireBackendUrl();
  const headers = new Headers(init.headers);
  for (const [key, value] of Object.entries(requireBackendAuthHeaders(cookies))) {
    headers.set(key, String(value));
  }
  if (!headers.has('x-request-id')) {
    headers.set('x-request-id', `fe-${randomUUID()}`);
  }

  let response: Response;
  try {
    response = await fetcher(`${backendUrl}${path}`, {
      ...init,
      headers
    });
  } catch (err) {
    await reportFailureTicketToBackend(fetcher, cookies, {
      apiPath: path,
      errorName: err instanceof Error ? err.name : 'BackendRequestError',
      errorMessage: err instanceof Error ? err.message : 'Backend request failed before a response was received.',
      errorStack: err instanceof Error ? err.stack : null,
      severity: 'high',
      source: 'api',
      context: {
        method: init.method ?? 'GET',
        phase: 'fetch'
      }
    });
    throw error(503, fallbackMessage);
  }
  const payload = await parseJson(response);

  if (!response.ok) {
    await reportFailureTicketToBackend(fetcher, cookies, {
      apiPath: path,
      statusCode: response.status,
      errorName: 'BackendResponseError',
      errorMessage: extractErrorMessage(payload, fallbackMessage),
      severity: response.status >= 500 ? 'high' : 'medium',
      source: 'api',
      requestId: response.headers.get('x-request-id'),
      context: {
        method: init.method ?? 'GET',
        statusText: response.statusText
      }
    });
    throw error(response.status, extractErrorMessage(payload, fallbackMessage));
  }

  return json(payload, { status: response.status });
}
