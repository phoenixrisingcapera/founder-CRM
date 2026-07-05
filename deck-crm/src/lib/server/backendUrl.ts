import { env } from '$env/dynamic/private';

export const BACKEND_URL_ENV_NAME = 'DECK_AISTACK_BACKEND_URL' as const;
export const BACKEND_URL_ENV_NAMES = [
  BACKEND_URL_ENV_NAME,
  'BACKEND_URL',
  'API_BASE_URL',
  'DECK_BACKEND_URL',
  'BACKEND_API_URL',
  'PUBLIC_BACKEND_API_URL',
  'PUBLIC_DECK_AISTACK_BACKEND_URL'
] as const;

type BackendEnvSource = Record<string, string | undefined>;

function cleanBackendUrl(value: string | undefined) {
  const raw = (value ?? '').trim().replace(/\/+$/, '');
  if (!raw) return '';

  // Railway users often enter `api.deck.aistack.codes` instead of a fully
  // qualified URL. Node's server-side fetch requires a protocol, so normalize
  // bare hostnames here instead of crashing auth with "Failed to parse URL".
  if (/^https?:\/\//i.test(raw)) {
    return raw;
  }

  return `https://${raw}`;
}

function resolveBackendUrl(envSource: BackendEnvSource = env) {
  for (const name of BACKEND_URL_ENV_NAMES) {
    const resolved = cleanBackendUrl(envSource[name]);
    if (resolved) return resolved;
  }
  return '';
}

export const BACKEND_URL = resolveBackendUrl();
