import { error, json, type Cookies } from '@sveltejs/kit';
import { BACKEND_URL, extractErrorMessage, parseJson, requireBackendUrl } from '$server/backendApi';
import { requireBackendAuthHeaders } from '$server/backendAuth';

const validProviders = new Set(['microsoft', 'linkedin']);
const FALLBACK_SETTINGS = {
  user: {
    id: 'user_default',
    email: 'user@deck.aistack.codes',
    name: 'Deck AIStack User'
  },
  profile: {
    id: 'profile_user_default',
    userId: 'user_default',
    displayName: 'Deck AIStack User',
    headline: 'Workspace profile is managed by the backend.',
    companyName: 'Deck AIStack',
    jobTitle: null,
    department: null,
    city: null,
    region: null,
    country: null,
    timezone: null,
    preferredLanguage: 'en',
    photoUrl: null,
    bio: null,
    linkedinProfileUrl: null,
    microsoftTenantId: null,
    workEmail: 'user@deck.aistack.codes',
    mobilePhone: null,
    skillsJson: [],
    educationJson: [],
    certificationsJson: [],
    profileSourceJson: {
      mode: 'backend_required'
    }
  },
  connectedAccounts: []
};

async function backendJson(fetcher: typeof fetch, cookies: Cookies, path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  for (const [key, value] of Object.entries(requireBackendAuthHeaders(cookies))) {
    headers.set(key, String(value));
  }
  const response = await fetcher(`${BACKEND_URL}${path}`, {
    ...init,
    headers
  });
  const payload = await parseJson(response);
  if (!response.ok) {
    throw error(response.status, extractErrorMessage(payload, 'Could not load account settings.'));
  }
  return payload as Record<string, unknown>;
}

function normalizeProfile(profile: Record<string, unknown> | null | undefined, user: App.Locals['sessionUser']) {
  if (!profile) return null;

  return {
    id: String(profile.id ?? ''),
    userId: String(profile.userId ?? user?.id ?? ''),
    displayName: (profile.displayName as string | null | undefined) ?? user?.name ?? null,
    headline: (profile.headline as string | null | undefined) ?? null,
    companyName: (profile.companyName as string | null | undefined) ?? null,
    jobTitle: (profile.jobTitle as string | null | undefined) ?? null,
    department: (profile.department as string | null | undefined) ?? null,
    city: (profile.city as string | null | undefined) ?? null,
    region: null,
    country: (profile.country as string | null | undefined) ?? null,
    timezone: (profile.timezone as string | null | undefined) ?? null,
    preferredLanguage: (profile.preferredLanguage as string | null | undefined) ?? null,
    photoUrl: null,
    bio: null,
    linkedinProfileUrl: (profile.linkedinProfileUrl as string | null | undefined) ?? null,
    microsoftTenantId: null,
    workEmail: (profile.workEmail as string | null | undefined) ?? user?.email ?? null,
    mobilePhone: null,
    skillsJson: profile.skills ?? [],
    educationJson: profile.education ?? [],
    certificationsJson: profile.certifications ?? [],
    profileSourceJson: (profile.profileSource as Record<string, unknown> | null | undefined) ?? {}
  };
}

function normalizeAccount(account: Record<string, unknown>) {
  return {
    id: String(account.id ?? ''),
    provider: String(account.provider ?? ''),
    status: String(account.status ?? 'disconnected'),
    externalAccountId: (account.externalAccountId as string | null | undefined) ?? null,
    externalEmail: (account.externalEmail as string | null | undefined) ?? null,
    externalDisplayName: (account.externalDisplayName as string | null | undefined) ?? null,
    externalProfileUrl: (account.externalProfileUrl as string | null | undefined) ?? null,
    scopes: Array.isArray(account.scopes) ? account.scopes : [],
    accessTokenMasked: (account.accessTokenMasked as string | null | undefined) ?? null,
    refreshTokenStored: Boolean(account.refreshTokenStored),
    lastSyncedAt: (account.lastSyncedAt as string | null | undefined) ?? null,
    syncMetadataJson: (account.syncMetadata as Record<string, unknown> | null | undefined) ?? null
  };
}

export async function GET({ fetch, cookies, locals }) {
  if (!BACKEND_URL && locals.founderInspection.active) {
    return json({ settings: FALLBACK_SETTINGS });
  }

  requireBackendUrl();

  const [profilePayload, accountsPayload] = await Promise.all([
    backendJson(fetch, cookies, '/api/account/profile'),
    backendJson(fetch, cookies, '/api/account/connected-accounts')
  ]);

  const profile = normalizeProfile(profilePayload.profile as Record<string, unknown> | null | undefined, locals.sessionUser);
  const accounts = ((accountsPayload.accounts as Record<string, unknown>[] | undefined) ?? []).map(normalizeAccount);

  const settings = {
    user: {
      id: locals.sessionUser?.id ?? profile?.userId ?? '',
      email: locals.sessionUser?.email ?? profile?.workEmail ?? '',
      name: locals.sessionUser?.name ?? profile?.displayName ?? 'User'
    },
    profile,
    connectedAccounts: accounts
  };

  return json({ settings });
}

async function loadSettings(fetcher: typeof fetch, cookies: Cookies, user: App.Locals['sessionUser']) {
  const [profilePayload, accountsPayload] = await Promise.all([
    backendJson(fetcher, cookies, '/api/account/profile'),
    backendJson(fetcher, cookies, '/api/account/connected-accounts')
  ]);

  const profile = normalizeProfile(profilePayload.profile as Record<string, unknown> | null | undefined, user);
  const accounts = ((accountsPayload.accounts as Record<string, unknown>[] | undefined) ?? []).map(normalizeAccount);

  return {
    user: {
      id: user?.id ?? profile?.userId ?? '',
      email: user?.email ?? profile?.workEmail ?? '',
      name: user?.name ?? profile?.displayName ?? 'User'
    },
    profile,
    connectedAccounts: accounts
  };
}

export async function POST({ request, fetch, cookies, locals }) {
  const payload = await request.json();
  if (!payload.provider) throw error(400, 'provider is required');
  if (!validProviders.has(payload.provider)) throw error(400, 'provider is invalid');

  requireBackendUrl();

  await backendJson(fetch, cookies, '/api/account/connected-accounts', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      provider: payload.provider,
      origin: payload.origin ?? 'settings'
    })
  });

  return json({
    settings: await loadSettings(fetch, cookies, locals.sessionUser)
  });
}
