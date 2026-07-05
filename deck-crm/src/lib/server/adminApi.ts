import type { Cookies } from '@sveltejs/kit';
import { extractErrorMessage, parseJson, requireBackendUrl } from '$server/backendApi';
import { requireBackendAuthHeaders } from '$server/backendAuth';
import type {
  AdminAuditResponse,
  AdminAgentRun,
  AdminAgentRunDetail,
  AdminAgentRunNote,
  AdminAgentRunsResponse,
  AdminAgentTeamsResponse,
  AdminDeckProcessing,
  AdminDeckSlides,
  AdminElementsResponse,
  AdminFailureTicketDetail,
  AdminFailureTicketsResponse,
  AdminSafetyControls,
  AdminLearningMemoriesResponse,
  AdminUser,
  AdminUserRole,
  AdminOverview,
  AdminDeploymentReadinessResponse,
  AdminProviderHealthResponse,
  AdminQuotasResponse,
  AdminRegressionCase,
  AdminLearningMemory,
  AdminTelemetryEventsResponse,
  AdminTelemetryFailuresResponse,
  AdminTelemetryMetricsResponse,
  AdminTelemetryObservabilityResponse,
} from '$lib/types/admin';

async function fetchAdminJson<T>(
  fetcher: typeof fetch,
  cookies: Cookies,
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const backendUrl = requireBackendUrl();
  const headers = new Headers(init.headers);
  const authHeaders = requireBackendAuthHeaders(cookies) as Record<string, string>;
  for (const [key, value] of Object.entries(authHeaders)) {
    headers.set(key, value);
  }
  const response = await fetcher(`${backendUrl}${path}`, {
    ...init,
    headers
  });
  const payload = await parseJson(response);

  if (!response.ok) {
    throw new Error(extractErrorMessage(payload, `Admin request failed: ${response.status}`));
  }

  return payload as T;
}

export function loadAdminOverview(fetcher: typeof fetch, cookies: Cookies) {
  return fetchAdminJson<AdminOverview>(fetcher, cookies, '/api/admin/overview');
}

export function loadAdminUsers(fetcher: typeof fetch, cookies: Cookies) {
  return fetchAdminJson<AdminUser[]>(fetcher, cookies, '/api/admin/users');
}

export function updateAdminUserRole(fetcher: typeof fetch, cookies: Cookies, userId: string, role: AdminUserRole) {
  return fetchAdminJson<AdminUser>(
    fetcher,
    cookies,
    `/api/admin/users/${encodeURIComponent(userId)}/role`,
    {
      method: 'PATCH',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify({ role })
    }
  );
}

export function loadAdminAgentRuns(fetcher: typeof fetch, cookies: Cookies, limit = 100) {
  return fetchAdminJson<AdminAgentRunsResponse>(fetcher, cookies, `/api/admin/agents/runs?limit=${limit}`);
}

export function loadAdminAgentRunDetail(fetcher: typeof fetch, cookies: Cookies, runId: string) {
  return fetchAdminJson<AdminAgentRunDetail>(
    fetcher,
    cookies,
    `/api/admin/agents/runs/${encodeURIComponent(runId)}`
  );
}

export function loadAdminLearningMemories(fetcher: typeof fetch, cookies: Cookies, limit = 100) {
  return fetchAdminJson<AdminLearningMemoriesResponse>(
    fetcher,
    cookies,
    `/api/admin/learning-memories?limit=${limit}`
  );
}

export function loadAdminTelemetryEvents(
  fetcher: typeof fetch,
  cookies: Cookies,
  options: {
    limit?: number;
    runId?: string | null;
    deckId?: string | null;
    runType?: string | null;
    status?: string | null;
    eventName?: string | null;
  } = {}
) {
  const params = new URLSearchParams();
  params.set('limit', String(options.limit ?? 100));
  if (options.runId) params.set('runId', options.runId);
  if (options.deckId) params.set('deckId', options.deckId);
  if (options.runType) params.set('runType', options.runType);
  if (options.status) params.set('status', options.status);
  if (options.eventName) params.set('eventName', options.eventName);
  return fetchAdminJson<AdminTelemetryEventsResponse>(fetcher, cookies, `/api/admin/telemetry/events?${params.toString()}`);
}

export function loadAdminTelemetryMetrics(fetcher: typeof fetch, cookies: Cookies) {
  return fetchAdminJson<AdminTelemetryMetricsResponse>(fetcher, cookies, '/api/admin/telemetry/metrics');
}

export function loadAdminTelemetryFailures(
  fetcher: typeof fetch,
  cookies: Cookies,
  options: { limit?: number; runType?: string | null; deckId?: string | null } = {}
) {
  const params = new URLSearchParams();
  params.set('limit', String(options.limit ?? 25));
  if (options.runType) params.set('runType', options.runType);
  if (options.deckId) params.set('deckId', options.deckId);
  return fetchAdminJson<AdminTelemetryFailuresResponse>(
    fetcher,
    cookies,
    `/api/admin/telemetry/failures?${params.toString()}`
  );
}


export function loadAdminTelemetryObservability(fetcher: typeof fetch, cookies: Cookies) {
  return fetchAdminJson<AdminTelemetryObservabilityResponse>(
    fetcher,
    cookies,
    '/api/admin/telemetry/observability'
  );
}

export function promoteTelemetryFailureToLearningMemory(
  fetcher: typeof fetch,
  cookies: Cookies,
  eventId: string,
  note: string
) {
  return fetchAdminJson<{ memory: AdminLearningMemory }>(
    fetcher,
    cookies,
    `/api/admin/telemetry/failures/${encodeURIComponent(eventId)}/promote-learning-memory`,
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify({ note })
    }
  );
}

export function promoteTelemetryFailureToRegressionCase(
  fetcher: typeof fetch,
  cookies: Cookies,
  eventId: string,
  note: string
) {
  return fetchAdminJson<{ regressionCase: AdminRegressionCase }>(
    fetcher,
    cookies,
    `/api/admin/telemetry/failures/${encodeURIComponent(eventId)}/promote-regression`,
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify({ note })
    }
  );
}

export function loadAdminAgentTeams(fetcher: typeof fetch, cookies: Cookies) {
  return fetchAdminJson<AdminAgentTeamsResponse>(fetcher, cookies, '/api/admin/agent-teams');
}

export function createAdminAgentRunNote(fetcher: typeof fetch, cookies: Cookies, runId: string, note: string) {
  return fetchAdminJson<{ note: AdminAgentRunNote }>(
    fetcher,
    cookies,
    `/api/admin/agents/runs/${encodeURIComponent(runId)}/notes`,
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify({ note })
    }
  );
}

export function markAdminAgentRunFailed(fetcher: typeof fetch, cookies: Cookies, runId: string, reason: string) {
  return fetchAdminJson<{ run: AdminAgentRun; auditEvent: Record<string, unknown> }>(
    fetcher,
    cookies,
    `/api/admin/agents/runs/${encodeURIComponent(runId)}/mark-failed`,
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify({ reason, confirm: true })
    }
  );
}

export function cancelAdminAgentRun(fetcher: typeof fetch, cookies: Cookies, runId: string, reason: string) {
  return fetchAdminJson<{ run: AdminAgentRun; auditEvent: Record<string, unknown> }>(
    fetcher,
    cookies,
    `/api/admin/agents/runs/${encodeURIComponent(runId)}/cancel`,
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify({ reason, confirm: true })
    }
  );
}

export function discardAdminAgentRun(fetcher: typeof fetch, cookies: Cookies, runId: string, reason: string) {
  return fetchAdminJson<{ run: AdminAgentRun; auditEvent: Record<string, unknown> }>(
    fetcher,
    cookies,
    `/api/admin/agents/runs/${encodeURIComponent(runId)}/discard`,
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify({ reason, confirm: true })
    }
  );
}

export function retryAdminAgentRun(fetcher: typeof fetch, cookies: Cookies, runId: string, reason: string) {
  return fetchAdminJson<{
    run: AdminAgentRun;
    originalRun: AdminAgentRun;
    auditEvent: Record<string, unknown>;
  }>(
    fetcher,
    cookies,
    `/api/admin/agents/runs/${encodeURIComponent(runId)}/retry`,
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify({ reason, confirm: true })
    }
  );
}

export function loadAdminDeckProcessing(fetcher: typeof fetch, cookies: Cookies, deckId: string) {
  return fetchAdminJson<AdminDeckProcessing>(
    fetcher,
    cookies,
    `/api/admin/decks/${encodeURIComponent(deckId)}/processing`
  );
}

export function loadAdminDeckSlides(fetcher: typeof fetch, cookies: Cookies, deckId: string) {
  return fetchAdminJson<AdminDeckSlides>(fetcher, cookies, `/api/admin/decks/${encodeURIComponent(deckId)}/slides`);
}

export function loadAdminElements(
  fetcher: typeof fetch,
  cookies: Cookies,
  options: { deckId?: string | null; limit?: number } = {}
) {
  const params = new URLSearchParams();
  params.set('limit', String(options.limit ?? 100));
  if (options.deckId) params.set('deckId', options.deckId);
  return fetchAdminJson<AdminElementsResponse>(fetcher, cookies, `/api/admin/elements?${params.toString()}`);
}

export function loadAdminQuotas(fetcher: typeof fetch, cookies: Cookies, limit = 100) {
  return fetchAdminJson<AdminQuotasResponse>(fetcher, cookies, `/api/admin/quotas?limit=${limit}`);
}

export function loadAdminProviderHealth(fetcher: typeof fetch, cookies: Cookies, limit = 100) {
  return fetchAdminJson<AdminProviderHealthResponse>(fetcher, cookies, `/api/admin/provider-health?limit=${limit}`);
}

export function loadAdminDeploymentReadiness(fetcher: typeof fetch, cookies: Cookies) {
  return fetchAdminJson<AdminDeploymentReadinessResponse>(fetcher, cookies, '/api/admin/deployment-readiness');
}

export function loadAdminAudit(
  fetcher: typeof fetch,
  cookies: Cookies,
  options: {
    limit?: number;
    action?: string | null;
    result?: string | null;
    resourceType?: string | null;
    actor?: string | null;
  } = {}
) {
  const params = new URLSearchParams();
  params.set('limit', String(options.limit ?? 100));
  if (options.action) params.set('action', options.action);
  if (options.result) params.set('result', options.result);
  if (options.resourceType) params.set('resourceType', options.resourceType);
  if (options.actor) params.set('actor', options.actor);
  return fetchAdminJson<AdminAuditResponse>(fetcher, cookies, `/api/admin/audit?${params.toString()}`);
}

export function loadAdminFailureTickets(
  fetcher: typeof fetch,
  cookies: Cookies,
  options: {
    limit?: number;
    status?: string | null;
    severity?: string | null;
    source?: string | null;
    deckId?: string | null;
  } = {}
) {
  const params = new URLSearchParams();
  params.set('limit', String(options.limit ?? 100));
  if (options.status) params.set('status', options.status);
  if (options.severity) params.set('severity', options.severity);
  if (options.source) params.set('source', options.source);
  if (options.deckId) params.set('deckId', options.deckId);
  return fetchAdminJson<AdminFailureTicketsResponse>(
    fetcher,
    cookies,
    `/api/admin/failure-tickets?${params.toString()}`
  );
}

export function loadAdminFailureTicket(fetcher: typeof fetch, cookies: Cookies, ticketId: string) {
  return fetchAdminJson<AdminFailureTicketDetail>(
    fetcher,
    cookies,
    `/api/admin/failure-tickets/${encodeURIComponent(ticketId)}`
  );
}

export function loadAdminSafetyControls(fetcher: typeof fetch, cookies: Cookies) {
  return fetchAdminJson<AdminSafetyControls>(fetcher, cookies, '/api/admin/safety-controls');
}

export function updateAdminFailureTicket(
  fetcher: typeof fetch,
  cookies: Cookies,
  ticketId: string,
  payload: { status?: string; adminNotes?: string }
) {
  return fetchAdminJson<AdminFailureTicketDetail>(
    fetcher,
    cookies,
    `/api/admin/failure-tickets/${encodeURIComponent(ticketId)}`,
    {
      method: 'PATCH',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify(payload)
    }
  );
}
