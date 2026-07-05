import { error, json } from '@sveltejs/kit';
import { requireBackendAuthHeaders } from '$server/backendAuth';
import { BACKEND_URL, extractErrorMessage } from '$server/backendApi';

const EMPTY_SUMMARY = {
  provider: null,
  preferredModel: null,
  apiKeyLast4: null,
  isConfigured: false,
  configuredAt: null,
  skippedAt: null
};

function normalizeSummary(summary: Record<string, unknown>) {
  return {
    provider: summary.provider ?? null,
    preferredModel: summary.preferred_model ?? summary.preferredModel ?? null,
    apiKeyLast4: summary.api_key_last4 ?? summary.apiKeyLast4 ?? null,
    isConfigured: summary.is_configured ?? summary.isConfigured ?? false,
    configuredAt: summary.configured_at ?? summary.configuredAt ?? null,
    skippedAt: summary.skipped_at ?? summary.skippedAt ?? null
  };
}

function emptyProviderResponse(message: string, backendStatus?: number) {
  return json({
    summary: EMPTY_SUMMARY,
    degraded: true,
    backendStatus: backendStatus ?? null,
    message
  });
}

export async function GET({ fetch, cookies }) {
  if (BACKEND_URL) {
    let response: Response;
    try {
      response = await fetch(`${BACKEND_URL}/api/settings/workspace/ai-provider`, {
        headers: requireBackendAuthHeaders(cookies)
      });
    } catch {
      return emptyProviderResponse('Workspace AI provider is temporarily unavailable.');
    }

    const data = await response.json().catch(() => null);

    if (response.ok && data) {
      return json({ summary: normalizeSummary(data.summary ?? data) });
    }

    // Provider configuration is optional for browsing deck lists/intake. Do not
    // fail the whole page because this auxiliary summary could not be loaded.
    return emptyProviderResponse(
      extractErrorMessage(data, 'Workspace AI provider is not configured or could not be loaded.'),
      response.status
    );
  }

  return emptyProviderResponse('Backend URL is required for persisted workspace AI provider state.', 503);
}

export async function POST({ request, fetch, cookies }) {
  const payload = await request.json();

  if (BACKEND_URL) {
    const response = await fetch(`${BACKEND_URL}/api/settings/workspace/ai-provider`, {
      method: 'POST',
      headers: {
        ...requireBackendAuthHeaders(cookies),
        'content-type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json().catch(() => null);

    if (response.ok && data) {
      return json({
        summary: normalizeSummary(data.summary ?? data),
        nextUrl: data.next_url ?? data.nextUrl ?? '/welcome'
      });
    }

    throw error(response.status, extractErrorMessage(data, 'Could not save workspace AI provider.'));
  }

  throw error(503, 'Backend URL is required to save workspace AI provider state.');
}
