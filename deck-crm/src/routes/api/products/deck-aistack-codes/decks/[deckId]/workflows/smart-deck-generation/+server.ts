import { json, type RequestHandler } from '@sveltejs/kit';
import { deckProductApiPath } from '$lib/contracts';
import { readSmartDeckGenerationSubmission, submitWorkflowCommand } from '$server/services/workflowCommandService';

export const POST: RequestHandler = async ({ request, fetch, cookies }) => {
  const payload = await readSmartDeckGenerationSubmission(request);
  const accepted = await submitWorkflowCommand<Record<string, unknown>>(
    fetch,
    cookies,
    deckProductApiPath(`/decks/${payload.deckId}/workflows/smart-deck-generation`),
    'Smart Deck generation failed.',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: payload.instruction,
        selectedSourceSlideIds: payload.selectedSourceSlideIds,
        idempotencyKey: payload.idempotencyKey,
        sourceVersionId: null,
        deckType: payload.deckType,
        audience: payload.audience,
        preferredModel: payload.preferredModel,
        selectedElementId: payload.selectedElementId,
        selectedSubject: payload.selectedSubject,
        detectedSubjects: payload.detectedSubjects,
        actionId: payload.actionId,
        actionPrompt: payload.actionPrompt,
        userPrompt: payload.userPrompt,
        latestBatchId: payload.latestBatchId
      })
    }
  ) as Record<string, unknown>;

  return json({
    runId: String(accepted.jobId ?? ''),
    run_id: String(accepted.jobId ?? ''),
    deckId: payload.deckId,
    deck_id: payload.deckId,
    status: 'queued',
    intentType: 'redesign_slides',
    outputMode: 'editable_slide_versions',
    scope: payload.scope ?? 'selected_slides',
    selectedSlideIds: payload.selectedSourceSlideIds,
    batchId: null,
    design_version_id: null,
    state: 'queued',
    changed_slide_ids: [],
    generated_slides: [],
    generatedVersionIds: [],
    generatedVersionCount: 0,
    generationJob: {
      id: String(accepted.jobId ?? ''),
      deckId: payload.deckId,
      status: 'queued',
      prompt: payload.instruction,
      selectedSourceSlideIds: payload.selectedSourceSlideIds,
      createdAt: new Date().toISOString()
    },
    designVersion: null,
    workspace: null,
    errorMessage: null
  });
};
