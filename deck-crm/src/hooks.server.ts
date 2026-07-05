import type { Handle, HandleServerError } from '@sveltejs/kit';
import { buildFounderInspectionState } from '$lib/server/founderInspection';
import { readSessionUser } from '$lib/server/auth/session';
import { validateAuthSession } from '$lib/server/auth/authService';
import { reportFailureTicketToBackend } from '$lib/server/failureTickets';
import { isProductionRuntime } from '$lib/server/productionRuntime';
import { DECK_PRODUCT_API_PREFIX } from '$lib/contracts';

export const handle: Handle = async ({ event, resolve }) => {
  const isApiRequest = event.url.pathname.startsWith('/api/');
  const isDeckProductApiRequest = event.url.pathname.startsWith(DECK_PRODUCT_API_PREFIX);

  if (isDeckProductApiRequest) {
    // Product proxy routes forward the existing backend bearer token from the
    // cookie. Do not call backend /api/auth/me before every polling request;
    // a transient validation failure can otherwise clear the session cookie.
    event.locals.sessionUser = readSessionUser(event.cookies);
  } else if (isApiRequest) {
    const session = await validateAuthSession(event.cookies, { clearOnBackendAuthFailure: false });
    event.locals.sessionUser = session.user ?? readSessionUser(event.cookies);
  } else if (isProductionRuntime()) {
    event.locals.sessionUser = (await validateAuthSession(event.cookies)).user ?? null;
  } else {
    const session = await validateAuthSession(event.cookies);
    event.locals.sessionUser = session.user ?? readSessionUser(event.cookies);
  }

  event.locals.founderInspection = buildFounderInspectionState(event.locals.sessionUser);

  const response = await resolve(event);

  // Prevent browsers/proxies from holding stale SvelteKit HTML that points to
  // previous _app/immutable build assets after Railway deploys.
  const contentType = response.headers.get('content-type') ?? '';
  if (!event.url.pathname.startsWith('/_app/') && contentType.includes('text/html')) {
    response.headers.set('cache-control', 'no-store, max-age=0, must-revalidate');
    response.headers.set('pragma', 'no-cache');
    response.headers.set('expires', '0');
  }

  return response;
};

export const handleError: HandleServerError = async ({ error, event, status, message }) => {
  const errorValue = error instanceof Error ? error : null;
  await reportFailureTicketToBackend(event.fetch, event.cookies, {
    route: event.route.id,
    pageUrl: event.url.href,
    statusCode: status,
    userId: event.locals.sessionUser?.id ?? null,
    userEmail: event.locals.sessionUser?.email ?? null,
    errorName: errorValue?.name ?? 'ServerLoadError',
    errorMessage: errorValue?.message ?? message,
    errorStack: errorValue?.stack ?? null,
    severity: status >= 500 ? 'high' : 'medium',
    source: 'loader',
    context: {
      method: event.request.method,
      pathname: event.url.pathname
    }
  });

  return {
    message: 'Something went wrong. We have recorded the issue for review.'
  };
};
