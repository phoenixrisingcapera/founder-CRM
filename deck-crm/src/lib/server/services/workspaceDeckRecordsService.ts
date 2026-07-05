import { inferDeckFileType, type WorkspaceDeckRecord } from '$lib/components/deckService/upload/uploaded-decks-list.types';
import type { DeckFileType } from '$lib/contracts/types';

export function normalizeWorkspaceDeckRecord(payload: Record<string, unknown>): WorkspaceDeckRecord {
  const originalFilename = String(
    payload.originalFilename ??
      payload.original_filename ??
      payload.filename ??
      payload.title ??
      payload.displayName ??
      'Uploaded deck'
  );

  const mimeType = String(payload.mimeType ?? payload.mime_type ?? 'application/octet-stream');
  const filePayload = payload.file && typeof payload.file === 'object' ? (payload.file as { size?: unknown }) : null;
  const fileType: DeckFileType =
    typeof payload.fileType === 'string' && payload.fileType
      ? (payload.fileType as DeckFileType)
      : inferDeckFileType(originalFilename);

  return {
    id: String(payload.id ?? ''),
    workspaceId: String(payload.workspaceId ?? payload.workspace_id ?? 'ws_default'),
    displayName: String(payload.displayName ?? payload.display_name ?? payload.title ?? originalFilename),
    originalFilename,
    fileType,
    mimeType,
    fileSizeBytes:
      typeof payload.fileSizeBytes === 'number'
        ? payload.fileSizeBytes
        : typeof payload.file_size_bytes === 'number'
          ? payload.file_size_bytes
          : typeof filePayload?.size === 'number'
            ? filePayload.size
            : null,
    status: String(payload.status ?? 'uploaded'),
    thumbnailUrl:
      typeof payload.thumbnailUrl === 'string'
        ? payload.thumbnailUrl
        : typeof payload.thumbnail_url === 'string'
          ? payload.thumbnail_url
          : null,
    createdAt: String(payload.createdAt ?? payload.created_at ?? new Date().toISOString()),
    updatedAt: String(payload.updatedAt ?? payload.updated_at ?? new Date().toISOString())
  };
}
