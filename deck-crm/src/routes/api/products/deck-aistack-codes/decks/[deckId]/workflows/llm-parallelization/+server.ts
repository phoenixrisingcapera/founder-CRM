import { json, type RequestHandler } from '@sveltejs/kit';
import { deckProductApiPath } from '$lib/contracts';
import { readLlmParallelizationSubmission, submitWorkflowCommand } from '$server/services/workflowCommandService';

export const POST: RequestHandler = async ({ request, fetch, cookies }) => {
  const payload = await readLlmParallelizationSubmission(request);
  const accepted = await submitWorkflowCommand<Record<string, unknown>>(
    fetch,
    cookies,
    deckProductApiPath(`/decks/${payload.deckId}/workflows/llm-parallelization`),
    'LLM parallelization failed.',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: payload.prompt,
        selectedSourceSlideIds: payload.selectedSourceSlideIds,
        idempotencyKey: payload.idempotencyKey,
        partitionCount: payload.partitionCount,
        batchSize: payload.batchSize,
        preferredModel: payload.preferredModel
      })
    }
  );

  return json(accepted);
};
