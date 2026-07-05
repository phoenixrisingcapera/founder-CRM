type ApiErrorKind =
  | 'auth'
  | 'forbidden'
  | 'not_found'
  | 'validation'
  | 'api_contract'
  | 'backend'
  | 'network'
  | 'unknown';

type ApiErrorPayload = Record<string, unknown> | null;

class ApiClientError extends Error {
  status: number;
  kind: ApiErrorKind;
  requestId?: string | null;
  payload: ApiErrorPayload;
  path?: string;

  constructor(input: {
    message: string;
    status: number;
    kind: ApiErrorKind;
    requestId?: string | null;
    payload?: ApiErrorPayload;
    path?: string;
  }) {
    super(input.message);
    this.name = 'ApiClientError';
    this.status = input.status;
    this.kind = input.kind;
    this.requestId = input.requestId ?? null;
    this.payload = input.payload ?? null;
    this.path = input.path;
  }
}

export type ApiErrorBannerModel = {
  title: string;
  message: string;
  tone: 'danger' | 'warning' | 'info';
  status?: number;
  requestId?: string | null;
  actionLabel?: string;
  actionHref?: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function firstString(...values: unknown[]): string | undefined {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }

  return undefined;
}

function detailToString(detail: unknown): string | undefined {
  if (typeof detail === 'string' && detail.trim()) return detail.trim();
  const record = asRecord(detail);
  if (!record) return undefined;
  return firstString(record.message, record.error, record.reason, record.detail) ?? JSON.stringify(record);
}

function extractApiFailureCategory(payload: unknown): string | undefined {
  const record = asRecord(payload);
  if (!record) return undefined;
  const detail = asRecord(record.detail);
  return firstString(record.failureCategory, record.failure_category, detail?.failureCategory, detail?.failure_category);
}

function classifyApiStatus(status: number): ApiErrorKind {
  if (status === 401) return 'auth';
  if (status === 403) return 'forbidden';
  if (status === 404) return 'not_found';
  if (status === 400 || status === 422) return 'validation';
  if (status === 409 || status === 412 || status === 415) return 'api_contract';
  if (status >= 500) return 'backend';
  return 'unknown';
}

function extractApiErrorMessage(payload: unknown, fallback: string): string {
  const record = asRecord(payload);
  if (!record) return fallback;

  const detail = asRecord(record.detail);
  return (
    firstString(record.message, record.error, record.title, detail?.message, detail?.error, detail?.reason) ??
    detailToString(record.detail) ??
    fallback
  );
}

function apiErrorTitle(kind: ApiErrorKind): string {
  switch (kind) {
    case 'auth':
      return 'Sign-in required';
    case 'forbidden':
      return 'Access denied';
    case 'not_found':
      return 'Resource not found';
    case 'validation':
      return 'Request needs attention';
    case 'api_contract':
      return 'API contract mismatch';
    case 'backend':
      return 'Backend service error';
    case 'network':
      return 'Backend unavailable';
    default:
      return 'Request failed';
  }
}

function expandApiErrorMessage(
  kind: ApiErrorKind,
  message: string,
  status?: number,
  requestId?: string | null,
  failureCategory?: string
): string {
  const suffix = [
    status ? `status ${status}` : null,
    requestId ? `request ${requestId}` : null,
    failureCategory ? `category ${failureCategory}` : null
  ]
    .filter(Boolean)
    .join(', ');
  const suffixText = suffix ? ` (${suffix})` : '';

  if (kind === 'auth') {
    return `${message || 'Your session is missing or expired. Sign in again before using this workspace.'}${suffixText}`;
  }
  if (kind === 'forbidden') {
    return `${message || 'Your account does not have access to this deck or workspace.'}${suffixText}`;
  }
  if (kind === 'api_contract') {
    return `${message || 'The frontend and backend route contract do not match.'}${suffixText}`;
  }
  if (kind === 'backend') {
    return `${message || 'The backend returned an unexpected error. Check Railway backend logs.'}${suffixText}`;
  }
  if (kind === 'network') {
    return `${message || 'The frontend could not reach the backend. Check backend URL and deployment status.'}${suffixText}`;
  }

  return `${message}${suffixText}`;
}

export function toApiErrorBannerModel(error: unknown, fallbackTitle = 'Request failed'): ApiErrorBannerModel {
  if (error instanceof ApiClientError) {
    return {
      title: apiErrorTitle(error.kind),
      message: error.message,
      tone: error.kind === 'validation' || error.kind === 'not_found' ? 'warning' : 'danger',
      status: error.status,
      requestId: error.requestId,
      actionLabel: error.kind === 'auth' ? 'Sign in again' : undefined,
      actionHref: error.kind === 'auth' ? '/auth/sign-in' : undefined
    };
  }

  return {
    title: fallbackTitle,
    message: error instanceof Error ? error.message : 'The request failed before a structured backend response was available.',
    tone: 'danger'
  };
}

export async function readApiJsonOrThrow<T>(response: Response, fallbackMessage: string, path?: string): Promise<T> {
  const requestId = response.headers.get('x-request-id') ?? response.headers.get('x-railway-request-id');
  const raw = await response.text().catch(() => '');
  let payload: unknown = null;

  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = { message: raw };
    }
  }

  if (!response.ok) {
    const kind = classifyApiStatus(response.status);
    const baseMessage = extractApiErrorMessage(payload, fallbackMessage);
    const failureCategory = extractApiFailureCategory(payload);
    throw new ApiClientError({
      status: response.status,
      kind,
      requestId,
      payload: asRecord(payload),
      path,
      message: expandApiErrorMessage(kind, baseMessage, response.status, requestId, failureCategory)
    });
  }

  return payload as T;
}

export function isApiAuthError(error: unknown): boolean {
  return error instanceof ApiClientError && error.kind === 'auth';
}
