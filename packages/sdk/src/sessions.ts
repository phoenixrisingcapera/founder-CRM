import { ApiClient } from './client';
import type { SessionRecord } from '../../types/src/session';

export function listSessions(client = new ApiClient()): Promise<SessionRecord[]> {
  return client.get<SessionRecord[]>('/sessions');
}

export function getSession(sessionId: string, client = new ApiClient()): Promise<SessionRecord> {
  return client.get<SessionRecord>(`/sessions/${sessionId}`);
}
