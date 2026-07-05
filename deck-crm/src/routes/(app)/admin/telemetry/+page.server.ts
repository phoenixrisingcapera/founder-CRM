import { error, fail, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import {
  loadAdminTelemetryEvents,
  loadAdminTelemetryFailures,
  loadAdminTelemetryMetrics,
  loadAdminTelemetryObservability,
  promoteTelemetryFailureToLearningMemory,
  promoteTelemetryFailureToRegressionCase
} from '$server/adminApi';
import type { Actions } from './$types';

function validatePromotion(formData: FormData): { eventId: string; note: string } | { error: string } {
  const eventId = String(formData.get('eventId') ?? '').trim();
  const note = String(formData.get('note') ?? '').trim();
  if (!eventId) {
    return { error: 'Telemetry event is required.' };
  }
  if (note.length > 500) {
    return { error: 'Note must be 500 characters or fewer.' };
  }
  return { eventId, note };
}

export async function load({ cookies, fetch, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  const limit = Number(url.searchParams.get('limit') ?? 100);

  try {
    const [telemetry, metrics, failures, observability] = await Promise.all([
      loadAdminTelemetryEvents(fetch, cookies, {
        limit: Number.isFinite(limit) ? limit : 100,
        runId: url.searchParams.get('runId'),
        deckId: url.searchParams.get('deckId'),
        runType: url.searchParams.get('runType'),
        status: url.searchParams.get('status'),
        eventName: url.searchParams.get('eventName')
      }),
      loadAdminTelemetryMetrics(fetch, cookies),
      loadAdminTelemetryFailures(fetch, cookies, {
        limit: 25,
        runType: url.searchParams.get('runType'),
        deckId: url.searchParams.get('deckId')
      }),
      loadAdminTelemetryObservability(fetch, cookies)
    ]);

    return {
      telemetry,
      metrics,
      failures,
      observability,
      filters: {
        limit: Number.isFinite(limit) ? limit : 100,
        runId: url.searchParams.get('runId') ?? '',
        deckId: url.searchParams.get('deckId') ?? '',
        runType: url.searchParams.get('runType') ?? '',
        status: url.searchParams.get('status') ?? '',
        eventName: url.searchParams.get('eventName') ?? ''
      }
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'Admin telemetry is unavailable.');
  }
}

export const actions: Actions = {
  promoteLearning: async ({ cookies, fetch, request, url }) => {
    if (!getBackendAccessToken(cookies)) {
      throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
    }

    const validation = validatePromotion(await request.formData());
    if ('error' in validation) {
      return fail(400, { promotionError: validation.error });
    }

    try {
      await promoteTelemetryFailureToLearningMemory(fetch, cookies, validation.eventId, validation.note);
    } catch (err) {
      return fail(400, {
        promotionError: err instanceof Error ? err.message : 'Unable to promote telemetry failure to learning memory.'
      });
    }

    throw redirect(303, `${url.pathname}${url.search}`);
  },
  promoteRegression: async ({ cookies, fetch, request, url }) => {
    if (!getBackendAccessToken(cookies)) {
      throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
    }

    const validation = validatePromotion(await request.formData());
    if ('error' in validation) {
      return fail(400, { promotionError: validation.error });
    }

    try {
      await promoteTelemetryFailureToRegressionCase(fetch, cookies, validation.eventId, validation.note);
    } catch (err) {
      return fail(400, {
        promotionError: err instanceof Error ? err.message : 'Unable to promote telemetry failure to regression case.'
      });
    }

    throw redirect(303, `${url.pathname}${url.search}`);
  }
};
