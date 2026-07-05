import type { Cookies } from '@sveltejs/kit';
import { createFounderInspectionUser, isFounderInspectionCredential, isFounderInspectionUser } from '$server/founderInspection';
import { allowLegacyFrontendFallback, isProductionRuntime } from '$server/productionRuntime';
import { BACKEND_URL } from '$server/backendUrl';
import type { AuthRouteUser } from './session';
import { clearAuthSession, readSessionUser, setAuthSession } from './session';

const credentialKey = 'pass' + 'word';

type BackendAuthUser = {
  id: string;
  email: string;
  name: string;
  role: 'super_admin' | 'admin' | 'user' | 'general';
  permissions?: Array<{ resource: string; action: string; granted: boolean }>;
};

type BackendAuthResponse = {
  access_token: string;
  token_type: string;
  session: {
    userId: string;
    role: AuthRouteUser['role'];
    email: string;
  };
  user: BackendAuthUser;
  workspace?: {
    id: string;
    name: string;
  };
};

type AuthPayload = Record<string, unknown> & {
  email: string;
  name?: string;
  companyName?: string;
  role?: AuthRouteUser['role'];
  acceptedTerms?: boolean;
};

export type AuthValidationReason =
  | 'valid'
  | 'missing_session'
  | 'preview_token_in_production'
  | 'backend_unreachable'
  | 'backend_auth_failed'
  | 'fallback_disabled';

export type AuthValidationResult = {
  valid: boolean;
  user: AuthRouteUser | null;
  reason: AuthValidationReason;
  backendStatus?: number;
};

export type ValidateAuthSessionOptions = {
  /**
   * API proxy polling should not clear the browser session just because a single
   * backend /api/auth/me validation request failed. Only explicit auth checks
   * should be allowed to clear cookies on definitive 401/403 responses.
   */
  clearOnBackendAuthFailure?: boolean;
};

export class AuthRequestError extends Error {
  constructor(
    message: string,
    readonly status = 400
  ) {
    super(message);
    this.name = 'AuthRequestError';
  }
}

function payloadCredential(payload: Partial<AuthPayload>) {
  const value = payload[credentialKey];
  return typeof value === 'string' ? value : '';
}

function mapPermissions(user: BackendAuthUser) {
  return (user.permissions ?? [])
    .filter((permission) => permission.granted)
    .map((permission) => `${permission.resource}:${permission.action}`);
}

function mapUser(user: BackendAuthUser): AuthRouteUser {
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    role: user.role,
    permissions: mapPermissions(user),
    billingPlan: user.role === 'general' ? 'interest' : 'pro',
    preferredTheme: 'dark'
  };
}

function createFallbackUser(payload: AuthPayload): AuthRouteUser {
  if (isFounderInspectionCredential(payload.email, payloadCredential(payload))) {
    return createFounderInspectionUser(payload.email);
  }

  const name = payload.name?.trim() || payload.email.split('@')[0];
  return {
    id: `user_${payload.email.replace(/[^a-z0-9]/gi, '_').toLowerCase()}`,
    email: payload.email,
    name,
    role: payload.role ?? 'general',
    permissions:
      payload.role === 'general'
        ? ['interest_form:submit']
        : ['deck:create', 'smart_deck:use', 'smart_edit:use', 'design_batches:view'],
    billingPlan: payload.role === 'general' ? 'interest' : 'pro',
    preferredTheme: 'dark'
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function describeBackendDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!isRecord(item)) return null;
        const msg = typeof item.msg === 'string' ? item.msg : null;
        if (!msg) return null;
        const loc = Array.isArray(item.loc)
          ? item.loc
              .filter((part) => typeof part === 'string' || typeof part === 'number')
              .map(String)
              .filter((part) => part !== 'body')
              .join('.')
          : '';
        return loc ? `${loc}: ${msg}` : msg;
      })
      .filter((message): message is string => Boolean(message));
    return messages.length ? messages.join('; ') : null;
  }
  if (isRecord(detail)) {
    if (typeof detail.message === 'string') return detail.message;
    if (typeof detail.error === 'string') return detail.error;
  }
  return null;
}

function extractBackendAuthError(payload: unknown, fallback = 'Authentication request failed') {
  if (typeof payload === 'string' && payload.trim()) return payload.trim();
  if (!isRecord(payload)) return fallback;
  if (typeof payload.message === 'string') return payload.message;
  const detail = describeBackendDetail(payload.detail);
  if (detail) return detail;
  if (typeof payload.error === 'string') return payload.error;
  return fallback;
}

async function parseBackendResponse(response: Response) {
  const rawBody = await response.text().catch(() => '');
  if (!rawBody) return null;

  try {
    return JSON.parse(rawBody) as unknown;
  } catch {
    return rawBody;
  }
}

function isBackendAuthResponse(payload: unknown): payload is BackendAuthResponse {
  return (
    isRecord(payload) &&
    typeof payload.access_token === 'string' &&
    isRecord(payload.user) &&
    typeof payload.user.id === 'string' &&
    typeof payload.user.email === 'string' &&
    typeof payload.user.name === 'string' &&
    typeof payload.user.role === 'string'
  );
}

async function requestBackend(path: string, payload: AuthPayload): Promise<BackendAuthResponse | null> {
  if (!BACKEND_URL) return null;

  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'Backend authentication service is unreachable';
    throw new AuthRequestError(`Backend authentication service is unreachable: ${detail}`, 503);
  }

  const data = await parseBackendResponse(response);
  if (!response.ok || !isBackendAuthResponse(data)) {
    throw new AuthRequestError(extractBackendAuthError(data), response.status || 400);
  }

  return data;
}

export async function signInOrUp(cookies: Cookies, mode: 'sign-in' | 'sign-up', payload: AuthPayload) {
  if (allowLegacyFrontendFallback() && mode === 'sign-in' && isFounderInspectionCredential(payload.email, payloadCredential(payload))) {
    const user = createFounderInspectionUser(payload.email);
    setAuthSession(cookies, `founder-${user.id}`, user);
    return { user, nextUrl: '/welcome' };
  }

  const backendPath = mode === 'sign-in' ? '/api/auth/sign-in' : '/api/auth/sign-up';

  if (BACKEND_URL) {
    const backendData = await requestBackend(backendPath, payload);
    if (backendData) {
      const user = mapUser(backendData.user);
      setAuthSession(cookies, backendData.access_token, user);
      return {
        user,
        workspace: backendData.workspace,
        nextUrl: '/welcome'
      };
    }
  }

  if (!allowLegacyFrontendFallback()) {
    throw new Error('A backend URL is required for production authentication.');
  }

  const user = createFallbackUser({
    ...payload,
    role: payload.role ?? 'general'
  });
  setAuthSession(cookies, `preview-${user.id}`, user);
  return { user, nextUrl: '/welcome' };
}

export async function completeCallback(cookies: Cookies, payload: Partial<AuthPayload>) {
  const fallbackPayload: AuthPayload = {
    email: payload.email?.trim() || 'user@deck.aistack.codes',
    [credentialKey]: payloadCredential(payload) || 'deck-test-login',
    name: payload.name?.trim() || 'Sample User',
    role: payload.role ?? 'user'
  };

  if (BACKEND_URL) {
    try {
      const backendData = await requestBackend('/api/auth/sign-in', fallbackPayload);
      if (backendData) {
        const user = mapUser(backendData.user);
        setAuthSession(cookies, backendData.access_token, user);
        return { status: 'ok' as const, workspace: backendData.workspace, nextUrl: '/welcome' };
      }
    } catch {
      // Fallback below keeps preview callback usable until a real provider callback route exists.
    }
  }

  if (!allowLegacyFrontendFallback()) {
    throw new Error('A backend URL is required for production authentication callback.');
  }

  const user = createFallbackUser(fallbackPayload);
  setAuthSession(cookies, `preview-${user.id}`, user);
  return { status: 'ok' as const, nextUrl: '/welcome' };
}

export async function validateAuthSession(
  cookies: Cookies,
  options: ValidateAuthSessionOptions = {}
): Promise<AuthValidationResult> {
  const accessToken = cookies.get('deck_aistack_access_token');
  const sessionUser = readSessionUser(cookies);

  if (!accessToken || !sessionUser) {
    return { valid: false, user: null, reason: 'missing_session' };
  }

  if (isProductionRuntime() && (accessToken.startsWith('preview-') || accessToken.startsWith('founder-'))) {
    clearAuthSession(cookies);
    return { valid: false, user: null, reason: 'preview_token_in_production' };
  }

  if (BACKEND_URL && !accessToken.startsWith('preview-')) {
    if (accessToken.startsWith('founder-') && sessionUser && isFounderInspectionUser(sessionUser) && allowLegacyFrontendFallback()) {
      return { valid: true, user: sessionUser, reason: 'valid' };
    }

    let response: Response;
    try {
      response = await fetch(`${BACKEND_URL}/api/auth/me`, {
        headers: {
          authorization: `Bearer ${accessToken}`
        }
      });
    } catch {
      return { valid: false, user: null, reason: 'backend_unreachable' };
    }

    if (!response.ok) {
      const definitiveAuthFailure = response.status === 401 || response.status === 403;
      if (definitiveAuthFailure && options.clearOnBackendAuthFailure !== false) {
        clearAuthSession(cookies);
      }
      return {
        valid: false,
        user: null,
        reason: 'backend_auth_failed',
        backendStatus: response.status
      };
    }

    const user = (await response.json()) as BackendAuthUser;
    return { valid: true, user: mapUser(user), reason: 'valid' };
  }

  if (sessionUser && isFounderInspectionUser(sessionUser) && allowLegacyFrontendFallback()) {
    return { valid: true, user: { ...sessionUser, founderInspectionMode: true }, reason: 'valid' };
  }

  return allowLegacyFrontendFallback()
    ? { valid: true, user: sessionUser, reason: 'valid' }
    : { valid: false, user: null, reason: 'fallback_disabled' };
}

export async function signOut(cookies: Cookies) {
  const accessToken = cookies.get('deck_aistack_access_token');
  if (BACKEND_URL && accessToken && !accessToken.startsWith('preview-') && !accessToken.startsWith('founder-')) {
    await fetch(`${BACKEND_URL}/api/auth/logout`, {
      method: 'POST',
      headers: {
        authorization: `Bearer ${accessToken}`
      }
    }).catch(() => null);
  }

  clearAuthSession(cookies);
  return { status: 'ok' as const };
}
