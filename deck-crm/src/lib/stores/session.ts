import { writable } from 'svelte/store';
import { validateSession } from '$lib/api/auth';
import { deckServiceClient } from '$lib/api/deckServiceClient';

export type UserRole = 'super_admin' | 'admin' | 'user';

export type SessionUser = {
  id: string;
  email: string;
  role: UserRole;
  preferredTheme: 'light' | 'dark';
  billingPlan: string;
  permissions: string[];
  founderInspectionMode?: boolean;
};

export type InspectionState = {
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

export type SessionState = {
  status: 'loading' | 'authenticated' | 'anonymous';
  user: SessionUser | null;
  billingPlan: string;
  permissions: string[];
  inspection: InspectionState | null;
};

const initialState: SessionState = {
  status: 'loading',
  user: null,
  billingPlan: 'free',
  permissions: [],
  inspection: null
};

function createSessionStore() {
  const { subscribe, set, update } = writable<SessionState>(initialState);

  async function load() {
    update((state) => ({ ...state, status: 'loading' }));

    try {
      const [authResult, userResult, billingResult] = await Promise.allSettled([
        validateSession(),
        deckServiceClient.getCurrentUser(),
        deckServiceClient.getBillingState()
      ]);

      const authenticated =
        authResult.status === 'fulfilled' ? authResult.value.valid !== false : false;
      const inspection = authResult.status === 'fulfilled' ? authResult.value.inspection ?? null : null;

      if (!authenticated) {
        set({
          status: 'anonymous',
          user: null,
          billingPlan: 'free',
          permissions: [],
          inspection
        });
        return;
      }

      if (userResult.status !== 'fulfilled') {
        set({
          status: 'anonymous',
          user: null,
          billingPlan: 'free',
          permissions: [],
          inspection
        });
        return;
      }

      const user = userResult.value.user;
      const billingPlan =
        billingResult.status === 'fulfilled'
          ? billingResult.value.plan ?? user.billingPlan
          : user.billingPlan;

      set({
        status: 'authenticated',
        user: { ...user, billingPlan },
        billingPlan,
        permissions: user.permissions,
        inspection: userResult.value.inspection ?? inspection
      });
    } catch {
      set({
        status: 'anonymous',
        user: null,
        billingPlan: 'free',
        permissions: [],
        inspection: null
      });
    }
  }

  function hasPermission(permission: string) {
    let allowed = false;
    subscribe((state) => {
      allowed = state.permissions.includes(permission);
    })();
    return allowed;
  }

  return { subscribe, load, hasPermission };
}

export const sessionState = createSessionStore();
