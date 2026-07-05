type InspectionResponse = {
  enabled: boolean;
  active: boolean;
  founderEmail: string | null;
  hasPassword: boolean;
  backendConfigured: boolean;
  bypasses: {
    routeAccess: boolean;
    billing: boolean;
    providers: boolean;
  };
};

type SessionValidationResponse = {
  valid: boolean;
  inspection?: InspectionResponse;
};

export function validateSession() {
  return requestAuthRoute<SessionValidationResponse>('/session/validate');
}

type SignInRequest = {
  email: string;
  password: string;
};

type SignUpRequest = {
  name: string;
  email: string;
  password: string;
  companyName?: string;
  role?: 'general' | 'user';
  acceptedTerms: boolean;
};

type AuthRouteResponse = {
  nextUrl: string;
  user: {
    id: string;
    email: string;
    name: string;
    role: 'super_admin' | 'admin' | 'user' | 'general';
  };
  workspace?: {
    id: string;
    name: string;
  };
};

async function requestAuthRoute<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/auth${path}`, {
    method: body ? 'POST' : 'GET',
    credentials: 'include',
    headers: body ? { 'content-type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined
  });
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(extractAuthErrorMessage(payload));
  }

  return payload as T;
}

function extractAuthErrorMessage(payload: unknown) {
  if (!payload || typeof payload !== 'object') return 'Authentication request failed.';
  const record = payload as Record<string, unknown>;
  if (typeof record.message === 'string') return record.message;
  if (typeof record.detail === 'string') return record.detail;
  if (record.detail && typeof record.detail === 'object') {
    const detail = record.detail as Record<string, unknown>;
    if (typeof detail.message === 'string') return detail.message;
    if (typeof detail.error === 'string') return detail.error;
  }
  if (typeof record.error === 'string') return record.error;
  return 'Authentication request failed.';
}

export function signIn(payload: SignInRequest) {
  return requestAuthRoute<AuthRouteResponse>('/sign-in', payload);
}

export function signUp(payload: SignUpRequest) {
  return requestAuthRoute<AuthRouteResponse>('/sign-up', payload);
}

export function completeAuthCallback(payload: Partial<SignUpRequest & SignInRequest>) {
  return requestAuthRoute<{ status: 'ok'; nextUrl: string }>('/callback', payload);
}
