import { error } from '@sveltejs/kit';
import { BACKEND_URL, extractErrorMessage } from '$server/backendApi';
import { BACKEND_URL_ENV_NAME } from '$server/backendUrl';

export const SUPPORTED_DECK_EXTENSIONS = ['.pdf', '.ppt', '.pptx'] as const;
export const SUPPORTED_DECK_MIME_TYPES = new Set([
  'application/pdf',
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation'
]);
export const SUPPORTED_LOGO_EXTENSIONS = ['.gif', '.jpg', '.jpeg', '.png', '.webp'] as const;
export const SUPPORTED_LOGO_MIME_TYPES = new Set(['image/gif', 'image/jpeg', 'image/png', 'image/webp']);
export const SUPPORTED_BRAND_GUIDE_EXTENSIONS = ['.doc', '.docx', '.md', '.pdf', '.txt'] as const;
export const SUPPORTED_BRAND_GUIDE_MIME_TYPES = new Set([
  'application/msword',
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/markdown',
  'text/plain'
]);

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

export function isSupportedDeckUpload(file: File) {
  const lowerCaseName = file.name.toLowerCase();
  return SUPPORTED_DECK_MIME_TYPES.has(file.type) || SUPPORTED_DECK_EXTENSIONS.some((extension) => lowerCaseName.endsWith(extension));
}

export function isSupportedUpload(file: File, extensions: readonly string[], mimeTypes: Set<string>) {
  const lowerCaseName = file.name.toLowerCase();
  return mimeTypes.has(file.type) || extensions.some((extension) => lowerCaseName.endsWith(extension));
}

export function firstString(form: FormData, ...keys: string[]) {
  for (const key of keys) {
    const value = form.get(key);
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }

  return '';
}

export function stringList(form: FormData, ...keys: string[]) {
  return keys.flatMap((key) => form.getAll(key)).filter((value): value is string => typeof value === 'string' && value.trim().length > 0);
}

export function firstFile(form: FormData, ...keys: string[]) {
  for (const key of keys) {
    const value = form.get(key);
    if (value instanceof File && value.size > 0) {
      return value;
    }
  }

  return null;
}

export function firstPayloadValue(payload: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const value = payload[key];
    if (value !== undefined && value !== null && value !== '') {
      return value;
    }
  }

  return undefined;
}

export function textOrNull(value: unknown) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

export function detailRecord(payload: unknown): Record<string, unknown> | null {
  const record = asRecord(payload);
  if (!record) return null;
  return asRecord(record.detail) ?? record;
}

export function responseHeaders(requestId?: string | null) {
  return requestId ? { 'x-request-id': requestId } : undefined;
}

export function uploadContext(file: File, failureCategory: string, extra: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    failureCategory,
    backendUrlConfigured: Boolean(BACKEND_URL),
    fileName: file.name,
    fileExtension: file.name.split('.').pop()?.toLowerCase() ?? '',
    mimeType: file.type || 'application/octet-stream',
    size: file.size,
    ...extra
  };
}

export function normalizeUploadFailure(
  payload: unknown,
  status: number,
  fallbackMessage: string,
  responseRequestId?: string | null
): Record<string, unknown> {
  const detail = detailRecord(payload);
  const safeDetail = detail ?? {};
  const requestId =
    textOrNull(firstPayloadValue(safeDetail, 'requestId', 'request_id')) ??
    textOrNull(responseRequestId) ??
    null;
  const failureCategory =
    textOrNull(firstPayloadValue(safeDetail, 'failureCategory', 'failure_category')) ??
    'backend_upload_response_error';

  return {
    ok: false,
    message: extractErrorMessage(payload, fallbackMessage),
    status,
    requestId,
    failureCategory,
    ticketId: firstPayloadValue(safeDetail, 'ticketId', 'ticket_id') ?? null,
    errorName: firstPayloadValue(safeDetail, 'errorName', 'error_name') ?? null,
    detail
  };
}

export function normalizeUpload(payload: Record<string, unknown>) {
  return {
    deckId: payload.deckId ?? payload.deck_id,
    deckExtractionStatus: String(
      firstPayloadValue(payload, 'deck_extraction_status', 'deckExtractionStatus', 'state', 'status') ?? 'uploaded'
    ),
    confirmation: payload.confirmation ?? null
  };
}

export function requireBackend() {
  const backendUrl = (BACKEND_URL ?? '').trim().replace(/\/$/, '');
  if (!backendUrl) {
    throw error(503, `Backend URL is required for persisted deck uploads. Set ${BACKEND_URL_ENV_NAME}.`);
  }
  return backendUrl;
}

export function withRequestId(request: Request, headers: HeadersInit = {}) {
  const requestId = request.headers.get('x-request-id')?.trim();
  if (!requestId) {
    return headers;
  }

  return {
    ...headers,
    'x-request-id': requestId
  };
}
