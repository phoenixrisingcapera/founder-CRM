import { ApiClient } from './client';
import type { NoteRecord } from '../../types/src/note';

export function listNotes(
  options: { entityType?: string; entityId?: string } = {},
  client = new ApiClient(),
): Promise<NoteRecord[]> {
  const params = new URLSearchParams();
  if (options.entityType) {
    params.set('entity_type', options.entityType);
  }
  if (options.entityId) {
    params.set('entity_id', options.entityId);
  }
  const suffix = params.size ? `?${params.toString()}` : '';
  return client.get<NoteRecord[]>(`/notes${suffix}`);
}

export function getNote(noteId: string, client = new ApiClient()): Promise<NoteRecord> {
  return client.get<NoteRecord>(`/notes/${noteId}`);
}
