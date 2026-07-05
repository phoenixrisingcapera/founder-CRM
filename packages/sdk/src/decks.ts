import { ApiClient } from './client';
import type { DeckAssistantResponseRecord, DeckRecord } from '../../types/src/deck';

export function listDecks(client = new ApiClient()): Promise<DeckRecord[]> {
  return client.get<DeckRecord[]>('/decks');
}

export function createDeck(payload: Record<string, unknown>, client = new ApiClient()): Promise<DeckRecord> {
  return client.post<DeckRecord>('/decks', payload);
}

export function getDeck(deckId: string, client = new ApiClient()): Promise<DeckRecord> {
  return client.get<DeckRecord>(`/decks/${deckId}`);
}

export function getSharedDeck(shareToken: string, client = new ApiClient()): Promise<DeckRecord> {
  return client.get<DeckRecord>(`/decks/share/${shareToken}`);
}

export function createDeckAssistantIteration(
  deckId: string,
  payload: { instruction: string; scope: string; selected_slide_ids: string[] },
  client = new ApiClient(),
): Promise<DeckAssistantResponseRecord> {
  return client.post<DeckAssistantResponseRecord>(`/decks/${deckId}/assistant`, payload);
}
