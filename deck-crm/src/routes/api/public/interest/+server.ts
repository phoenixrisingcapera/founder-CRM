import { error, json } from '@sveltejs/kit';
import { extractErrorMessage, requireBackendUrl } from '$server/backendApi';

function publicInterestHeaders(request: Request): HeadersInit {
  const headers: Record<string, string> = {
    'content-type': 'application/json'
  };

  const requestId = request.headers.get('x-request-id')?.trim();
  if (requestId) {
    headers['x-request-id'] = requestId;
  }

  const forwardedFor = request.headers.get('x-forwarded-for')?.trim();
  if (forwardedFor) {
    headers['x-forwarded-for'] = forwardedFor;
  }

  const realIp = request.headers.get('x-real-ip')?.trim();
  if (realIp) {
    headers['x-real-ip'] = realIp;
  }

  return headers;
}

async function parsePublicInterestPayload(request: Request): Promise<unknown> {
  try {
    return await request.json();
  } catch {
    throw error(400, 'Public interest payload must be valid JSON.');
  }
}

export async function POST({ request, fetch }) {
  const backendUrl = requireBackendUrl();
  const payload = await parsePublicInterestPayload(request);

  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/public/interest`, {
      method: 'POST',
      headers: publicInterestHeaders(request),
      body: JSON.stringify(payload)
    });
  } catch (err) {
    const detail = err instanceof Error && err.message ? ` ${err.message}` : '';
    throw error(503, `Backend unavailable for public interest submissions.${detail}`);
  }

  const data = await response.json().catch(() => ({
    ok: false,
    message: 'Failed to submit public interest.'
  }));

  if (!response.ok) {
    throw error(response.status, extractErrorMessage(data, 'Failed to submit public interest.'));
  }

  return json(data, { status: response.status });
}
