import { redirect } from '@sveltejs/kit';

export function load({ locals, url }) {
  if (!locals.sessionUser) {
    const next = `${url.pathname}${url.search}`;
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(next)}`);
  }

  return {};
}
