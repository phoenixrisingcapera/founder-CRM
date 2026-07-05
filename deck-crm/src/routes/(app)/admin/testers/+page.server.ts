import { error, fail, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import { loadAdminUsers, updateAdminUserRole } from '$server/adminApi';
import type { AdminUser, AdminUserRole } from '$lib/types/admin';
import type { Actions } from './$types';

const VALID_TESTER_ROLES: AdminUserRole[] = ['general', 'user'];

function validateTesterAction(formData: FormData): { userId: string; role: AdminUserRole } | { error: string } {
  const userId = String(formData.get('userId') ?? '').trim();
  const role = String(formData.get('role') ?? '').trim();

  if (!userId) {
    return { error: 'Tester action requires a user identifier.' };
  }
  if (!VALID_TESTER_ROLES.includes(role as AdminUserRole)) {
    return { error: 'Tester action must be set to general or user.' };
  }

  return { userId, role: role as AdminUserRole };
}

export async function load({ cookies, fetch, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  try {
    const users = await loadAdminUsers(fetch, cookies);
    const testerUsers = users
      .filter((user: AdminUser) => ['general', 'user'].includes(user.role))
      .sort((a, b) => {
        const aTime = Date.parse((a.createdAt ?? a.created_at ?? '') || '0');
        const bTime = Date.parse((b.createdAt ?? b.created_at ?? '') || '0');
        return bTime - aTime;
      });

    return {
      testerUsers
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'Tester directory is unavailable.');
  }
}

export const actions: Actions = {
  setTesterRole: async ({ cookies, fetch, request, url }) => {
    if (!getBackendAccessToken(cookies)) {
      throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
    }

    const validation = validateTesterAction(await request.formData());
    if ('error' in validation) {
      return fail(400, { message: validation.error });
    }

    try {
      await updateAdminUserRole(fetch, cookies, validation.userId, validation.role);
    } catch (err) {
      return fail(400, {
        message: err instanceof Error ? err.message : 'Could not update tester role.'
      });
    }

    throw redirect(303, `/admin/testers${url.search}`);
  }
};
