import { error, fail, redirect } from '@sveltejs/kit';
import { getBackendAccessToken } from '$server/backendAuth';
import {
  cancelAdminAgentRun,
  createAdminAgentRunNote,
  discardAdminAgentRun,
  loadAdminAgentRunDetail,
  markAdminAgentRunFailed,
  retryAdminAgentRun
} from '$server/adminApi';
import type { Actions } from './$types';

function validateReasonAction(formData: FormData): { reason: string; error?: never } | { reason?: never; error: string } {
  const reason = String(formData.get('reason') ?? '').trim();
  const confirmed = formData.get('confirm') === 'yes';
  if (!reason) {
    return { error: 'Reason is required.' };
  }
  if (reason.length > 500) {
    return { error: 'Reason must be 500 characters or fewer.' };
  }
  if (!confirmed) {
    return { error: 'Confirmation is required.' };
  }
  return { reason };
}

export async function load({ cookies, fetch, params, url }) {
  if (!getBackendAccessToken(cookies)) {
    throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
  }

  try {
    return {
      detail: await loadAdminAgentRunDetail(fetch, cookies, params.runId)
    };
  } catch (err) {
    throw error(503, err instanceof Error ? err.message : 'Admin agent run detail is unavailable.');
  }
}

export const actions: Actions = {
  addNote: async ({ cookies, fetch, params, request, url }) => {
    if (!getBackendAccessToken(cookies)) {
      throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
    }

    const formData = await request.formData();
    const note = String(formData.get('note') ?? '').trim();
    if (!note) {
      return fail(400, { noteError: 'Note is required.' });
    }
    if (note.length > 2000) {
      return fail(400, { noteError: 'Note must be 2000 characters or fewer.' });
    }

    try {
      await createAdminAgentRunNote(fetch, cookies, params.runId, note);
    } catch (err) {
      return fail(400, {
        noteError: err instanceof Error ? err.message : 'Unable to add note to this run.'
      });
    }

    throw redirect(303, `/admin/agents/${encodeURIComponent(params.runId)}`);
  },
  markFailed: async ({ cookies, fetch, params, request, url }) => {
    if (!getBackendAccessToken(cookies)) {
      throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
    }

    const formData = await request.formData();
    const validation = validateReasonAction(formData);
    if ('error' in validation) {
      return fail(400, { markFailedError: validation.error });
    }

    try {
      await markAdminAgentRunFailed(fetch, cookies, params.runId, validation.reason);
    } catch (err) {
      return fail(400, {
        markFailedError: err instanceof Error ? err.message : 'Unable to mark this run failed.'
      });
    }

    throw redirect(303, `/admin/agents/${encodeURIComponent(params.runId)}`);
  },
  cancelRun: async ({ cookies, fetch, params, request, url }) => {
    if (!getBackendAccessToken(cookies)) {
      throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
    }

    const formData = await request.formData();
    const validation = validateReasonAction(formData);
    if ('error' in validation) {
      return fail(400, { cancelError: validation.error });
    }

    try {
      await cancelAdminAgentRun(fetch, cookies, params.runId, validation.reason);
    } catch (err) {
      return fail(400, {
        cancelError: err instanceof Error ? err.message : 'Unable to cancel this run.'
      });
    }

    throw redirect(303, `/admin/agents/${encodeURIComponent(params.runId)}`);
  },
  discardRun: async ({ cookies, fetch, params, request, url }) => {
    if (!getBackendAccessToken(cookies)) {
      throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
    }

    const formData = await request.formData();
    const validation = validateReasonAction(formData);
    if ('error' in validation) {
      return fail(400, { discardError: validation.error });
    }

    try {
      await discardAdminAgentRun(fetch, cookies, params.runId, validation.reason);
    } catch (err) {
      return fail(400, {
        discardError: err instanceof Error ? err.message : 'Unable to discard this design version.'
      });
    }

    throw redirect(303, `/admin/agents/${encodeURIComponent(params.runId)}`);
  },
  retryRun: async ({ cookies, fetch, params, request, url }) => {
    if (!getBackendAccessToken(cookies)) {
      throw redirect(303, `/auth/sign-in?next=${encodeURIComponent(`${url.pathname}${url.search}`)}`);
    }

    const formData = await request.formData();
    const validation = validateReasonAction(formData);
    if ('error' in validation) {
      return fail(400, { retryError: validation.error });
    }

    let replacementRunId = params.runId;
    try {
      const result = await retryAdminAgentRun(fetch, cookies, params.runId, validation.reason);
      replacementRunId = result.run.id;
    } catch (err) {
      return fail(400, {
        retryError: err instanceof Error ? err.message : 'Unable to retry this run.'
      });
    }

    throw redirect(303, `/admin/agents/${encodeURIComponent(replacementRunId)}`);
  }
};
