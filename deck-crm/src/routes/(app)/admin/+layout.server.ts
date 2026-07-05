import { redirect } from '@sveltejs/kit';

function canViewAdmin(user: App.Locals['sessionUser']) {
  return user?.role === 'super_admin';
}

export function load({ locals }) {
  if (!canViewAdmin(locals.sessionUser)) {
    throw redirect(303, '/welcome?notice=admin-internal');
  }

  return {
    adminUser: locals.sessionUser
  };
}
