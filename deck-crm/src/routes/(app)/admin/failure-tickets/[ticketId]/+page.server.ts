import { error, fail, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import { loadAdminFailureTicket, updateAdminFailureTicket } from '$server/adminApi';

export async function load({ cookies, fetch, params, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  try {
    return {
      failureTicket: await loadAdminFailureTicket(fetch, cookies, params.ticketId)
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'Failure ticket detail is unavailable.');
  }
}

export const actions = {
  update: async ({ request, fetch, cookies, params }) => {
    const form = await request.formData();
    const status = String(form.get('status') ?? '');
    const adminNotes = String(form.get('adminNotes') ?? '');
    try {
      await updateAdminFailureTicket(fetch, cookies, params.ticketId, { status, adminNotes });
    } catch (err) {
      return fail(400, { message: err instanceof Error ? err.message : 'Could not update the ticket.' });
    }

    throw redirect(303, `/admin/failure-tickets/${encodeURIComponent(params.ticketId)}`);
  }
};
