import { error } from '@sveltejs/kit';
import { deckProductApiPath } from '$lib/contracts';

export async function load({ fetch }) {
  const response = await fetch(deckProductApiPath('/workspace-summary'));
  if (!response.ok) throw error(response.status, 'Could not load workspace summary.');
  const payload = await response.json();
  return {
    workspace: payload.workspace,
    decks: payload.workspace.latestDecks ?? []
  };
}
