import { json } from '@sveltejs/kit';
import { fetchSmartDeckReadiness } from '$server/deckWorkflowProxy';

export async function GET({ params, fetch, cookies }) {
  const payload = await fetchSmartDeckReadiness(fetch, cookies, params.deckId);
  return json(payload);
}
