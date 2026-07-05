import { error, redirect } from '@sveltejs/kit';

function canViewAdminSlides(user: App.Locals['sessionUser']) {
  return user?.role === 'super_admin' || user?.role === 'admin' || user?.permissions.includes('admin:access');
}

export function load({ params, locals }) {
  if (!canViewAdminSlides(locals.sessionUser)) {
    throw error(403, 'Admin access required');
  }

  throw redirect(308, `/admin/slides/${params.deckId}`);
}
