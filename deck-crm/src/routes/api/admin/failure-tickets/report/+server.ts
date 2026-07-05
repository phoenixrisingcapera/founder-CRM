import { json } from '@sveltejs/kit';
import { reportFailureTicketToBackend } from '$server/failureTickets';

export async function POST({ request, fetch, cookies, locals, url }) {
  const payload = await request.json().catch(() => ({}));
  await reportFailureTicketToBackend(fetch, cookies, {
    ...payload,
    pageUrl: payload.pageUrl ?? request.headers.get('referer'),
    route: payload.route ?? url.pathname,
    userId: payload.userId ?? locals.sessionUser?.id ?? null,
    userEmail: payload.userEmail ?? locals.sessionUser?.email ?? null
  });

  return json({ status: 'recorded' });
}
