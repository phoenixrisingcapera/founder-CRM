import { error } from '@sveltejs/kit';
import { fetchWorkflowState } from '$server/deckWorkflowProxy';
import type { SmartDeckProcessingStatusWithDiagnostics } from '$lib/api/deckService/workflow.client';

export async function load({ params, fetch, cookies }) {
  try {
    const workflow = await fetchWorkflowState(fetch, cookies, params.deckId);
    return {
      deckId: params.deckId,
      workflow,
      status: workflow
    };
  } catch (thrown) {
    const candidate = thrown as { status?: number; body?: unknown };
    const body = candidate?.body && typeof candidate.body === 'object' ? (candidate.body as Record<string, unknown>) : null;
    if (candidate?.status === 404) {
      throw error(404, 'Deck processing status was not found.');
    }
    return {
      deckId: params.deckId,
      workflow: null,
      status: {
        deckId: params.deckId,
        status: 'failed',
        state: 'failed',
        deckExtractionStatus: 'failed',
        nextAction: 'view_processing',
        canOpenSmartDeck: false,
        canRetry: true,
        sourceFileSaved: false,
        message:
          (candidate?.body && typeof candidate.body === 'object' && 'message' in candidate.body
            ? String((candidate.body as Record<string, unknown>).message ?? '')
            : '') ||
          `Could not load deck processing status. Backend returned HTTP ${candidate?.status ?? 500}.`,
        errorMessage:
          (candidate?.body && typeof candidate.body === 'object' && 'message' in candidate.body
            ? String((candidate.body as Record<string, unknown>).message ?? '')
            : '') ||
          `Could not load deck processing status. Backend returned HTTP ${candidate?.status ?? 500}.`,
        phases: [
          {
            key: 'source_saved',
            label: 'Source file saved',
            status: 'pending',
            completed: false
          },
          {
            key: 'processing_status_unavailable',
            label: 'Processing status unavailable',
            description: `Could not load deck processing status. Backend returned HTTP ${candidate?.status ?? 500}.`,
            status: 'failed',
            active: false,
            completed: false
          }
        ],
        stages: [
          {
            key: 'source_saved',
            label: 'Source file saved',
            status: 'pending',
            completed: false
          },
          {
            key: 'processing_status_unavailable',
            label: 'Processing status unavailable',
            description: `Could not load deck processing status. Backend returned HTTP ${candidate?.status ?? 500}.`,
            status: 'failed',
            active: false,
            completed: false
          }
        ],
        processing: {
          state: 'failed',
          status: 'failed',
          message:
            (typeof body?.message === 'string' && body.message) ||
            `Could not load deck processing status. Backend returned HTTP ${candidate?.status ?? 500}.`,
          errorMessage:
            (typeof body?.message === 'string' && body.message) ||
            `Could not load deck processing status. Backend returned HTTP ${candidate?.status ?? 500}.`
        },
        smartDeck: {
          hasRenderableSchema: false,
          canOpenSmartDeck: false,
          schemaDebugUnavailable: true
        },
        backendStatus: candidate?.status ?? 500,
        backendStatusText: typeof body?.backendStatusText === 'string' ? body.backendStatusText : undefined,
        backendMessage:
          typeof body?.message === 'string'
            ? body.message
            : `Could not load deck processing status. Backend returned HTTP ${candidate?.status ?? 500}.`,
        backendPath: typeof body?.backendPath === 'string' ? body.backendPath : undefined,
        backendPayload: body?.backendPayload && typeof body.backendPayload === 'object' ? (body.backendPayload as Record<string, unknown>) : body
      } as SmartDeckProcessingStatusWithDiagnostics
    };
  }
}
