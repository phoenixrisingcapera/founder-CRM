import type { AuthRouteUser } from '$server/auth/session';

export type FounderInspectionState = {
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

const DISABLED_STATE: FounderInspectionState = {
  enabled: false,
  active: false,
  founderEmail: null,
  hasPassword: false,
  backendConfigured: false,
  bypasses: {
    routeAccess: false,
    billing: false,
    providers: false
  }
};

export function isFounderInspectionUser(
  user: Pick<AuthRouteUser, 'email' | 'founderInspectionMode'> | null | undefined
) {
  return false;
}

export function buildFounderInspectionState(
  user: Pick<AuthRouteUser, 'email' | 'founderInspectionMode'> | null | undefined
): FounderInspectionState {
  return DISABLED_STATE;
}

export function isFounderInspectionCredential(email: string, password: string) {
  return false;
}

export function createFounderInspectionUser(email: string): AuthRouteUser {
  throw new Error('Founder inspection mode has moved to the Deck local_testing harness.');
}
