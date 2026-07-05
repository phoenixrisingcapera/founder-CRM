import { json } from '@sveltejs/kit';
import { fetchWorkflowState } from '$server/deckWorkflowProxy';

export async function GET({ params, fetch, cookies }) {
  const payload = await fetchWorkflowState(fetch, cookies, params.deckId);
  return json(payload);
}
