import { error, fail, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import { loadAdminUsers, updateAdminUserRole } from '$server/adminApi';
import type { AdminUserRole } from '$lib/types/admin';
import type { Actions } from './$types';

const VALID_ROLES: AdminUserRole[] = ['general', 'user', 'admin', 'super_admin'];

function validateRoleChange(formData: FormData): { userId: string; role: AdminUserRole } | { error: string } {
  const userId = String(formData.get('userId') ?? '').trim();
  const role = String(formData.get('role') ?? '').trim();

  if (!userId) {
    return { error: 'User identifier is required.' };
  }
  if (!VALID_ROLES.includes(role as AdminUserRole)) {
    return { error: 'Role must be one of: general, user, admin, super_admin.' };
  }
  return { userId, role: role as AdminUserRole };
}

export async function load({ cookies, fetch, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  try {
    return {
      users: await loadAdminUsers(fetch, cookies)
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'User administration is unavailable.');
  }
}

export const actions: Actions = {
  updateRole: async ({ cookies, fetch, request, url }) => {
    if (!getBackendAccessToken(cookies)) {
      throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
    }

    const validation = validateRoleChange(await request.formData());
    if ('error' in validation) {
      return fail(400, { message: validation.error });
    }

    try {
      await updateAdminUserRole(fetch, cookies, validation.userId, validation.role);
    } catch (err) {
      return fail(400, {
        message: err instanceof Error ? err.message : 'Could not update user role.'
      });
    }

    throw redirect(303, `/admin/users${url.search}`);
  }
};
