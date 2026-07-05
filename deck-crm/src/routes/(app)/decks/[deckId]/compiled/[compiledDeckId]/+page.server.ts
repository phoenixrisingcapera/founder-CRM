import { error, type Cookies } from '@sveltejs/kit';
import { loadCompiledDeck } from '$server/services/compiledDeckService';

export async function load({ params, fetch, cookies }: { params: { deckId: string; compiledDeckId: string }; fetch: typeof globalThis.fetch; cookies: Cookies }) {
  const compiledDeck = await loadCompiledDeck(fetch, cookies, params.deckId, params.compiledDeckId);

  if (!compiledDeck) {
    throw error(404, 'Compiled deck not found.');
  }

  return {
    compiledDeck
  };
}
