type DeckAnalyticsPayload = {
  eventName: string;
  surface?: string;
  entityType?: string;
  entityId?: string;
  metadata?: Record<string, unknown>;
};

const SESSION_STORAGE_KEY = 'deck_aistack_analytics_session_id';

function getSessionId(): string {
  if (typeof sessionStorage === 'undefined') return 'server-session-unavailable';
  const existing = sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) return existing;
  const generated = `sess_${crypto.randomUUID?.() ?? Math.random().toString(36).slice(2)}`;
  sessionStorage.setItem(SESSION_STORAGE_KEY, generated);
  return generated;
}

export async function trackDeckEvent(deckId: string, payload: DeckAnalyticsPayload): Promise<void> {
  try {
    await fetch(`/api/decks/${deckId}/analytics/events`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        eventName: payload.eventName,
        surface: payload.surface ?? 'unknown',
        entityType: payload.entityType,
        entityId: payload.entityId,
        sessionId: getSessionId(),
        metadata: payload.metadata ?? {}
      })
    });
  } catch {
    // Analytics must never block the product workflow.
  }
}
