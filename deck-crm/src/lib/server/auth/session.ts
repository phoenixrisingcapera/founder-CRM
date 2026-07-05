import { env } from '$env/dynamic/private';
import type { Cookies } from '@sveltejs/kit';

export type AuthRouteUser = {
  id: string;
  email: string;
  name: string;
  role: 'super_admin' | 'admin' | 'user' | 'general';
  permissions: string[];
  billingPlan: string;
  preferredTheme: 'light' | 'dark';
  founderInspectionMode?: boolean;
};

export const AUTH_ACCESS_COOKIE = 'deck_aistack_access_token';
export const AUTH_USER_COOKIE = 'deck_aistack_session_user';

const DEFAULT_COOKIE_OPTIONS = {
  httpOnly: true,
  sameSite: 'lax' as const,
  secure: env.NODE_ENV === 'production',
  path: '/'
};

function encodeUser(user: AuthRouteUser) {
  return Buffer.from(JSON.stringify(user), 'utf-8').toString('base64url');
}

function decodeUser(value: string | undefined): AuthRouteUser | null {
  if (!value) return null;

  try {
    const parsed = JSON.parse(Buffer.from(value, 'base64url').toString('utf-8')) as AuthRouteUser;
    return parsed;
  } catch {
    return null;
  }
}

export function readSessionUser(cookies: Cookies) {
  return decodeUser(cookies.get(AUTH_USER_COOKIE));
}

export function setAuthSession(cookies: Cookies, accessToken: string, user: AuthRouteUser) {
  cookies.set(AUTH_ACCESS_COOKIE, accessToken, DEFAULT_COOKIE_OPTIONS);
  cookies.set(AUTH_USER_COOKIE, encodeUser(user), DEFAULT_COOKIE_OPTIONS);
}

export function clearAuthSession(cookies: Cookies) {
  cookies.delete(AUTH_ACCESS_COOKIE, { path: '/' });
  cookies.delete(AUTH_USER_COOKIE, { path: '/' });
}
