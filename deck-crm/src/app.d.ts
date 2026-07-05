import type { AuthRouteUser } from '$lib/server/auth/session';
import type { FounderInspectionState } from '$lib/server/founderInspection';

declare global {
  namespace App {
    interface Locals {
      sessionUser: AuthRouteUser | null;
      founderInspection: FounderInspectionState;
    }
  }
}

export {};
