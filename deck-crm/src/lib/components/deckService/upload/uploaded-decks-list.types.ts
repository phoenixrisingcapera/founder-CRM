import type { Deck } from '$types/domain';
import type { DeckFileType } from '$lib/contracts/types';

export type UploadedDeckListStatus = 'uploaded' | 'processing' | 'failed' | 'selected';

export interface WorkspaceDeckRecord {
  id: string;
  workspaceId: string;
  displayName: string;
  originalFilename: string;
  fileType: DeckFileType;
  mimeType: string;
  fileSizeBytes: number | null;
  status: string;
  thumbnailUrl?: string | null;
  createdAt: string;
  updatedAt: string;
}

interface UploadedDeck {
  id: string;
  name: string;
  fileType: DeckFileType;
  fileSizeBytes?: number | null;
  fileSizeLabel?: string | null;
  uploadedAt?: string | null;
  uploadedAtLabel?: string | null;
  status: UploadedDeckListStatus;
  thumbnailUrl?: string | null;
}

export interface UploadedDeckListItem extends UploadedDeck {
  fileKindLabel?: string;
}

export function mapDeckStatusToListStatus(status: string): UploadedDeckListStatus {
  const normalized = status.trim().toLowerCase();
  if (normalized === 'failed' || normalized === 'error' || normalized === 'dead_letter') return 'failed';
  if (normalized === 'selected') return 'selected';
  if (
    normalized === 'uploaded' ||
    normalized === 'queued' ||
    normalized === 'parsing' ||
    normalized === 'structuring' ||
    normalized === 'extracting_blocks' ||
    normalized === 'classifying_blocks' ||
    normalized === 'analysing' ||
    normalized === 'adapting' ||
    normalized === 'processing' ||
    normalized === 'running'
  ) {
    return 'processing';
  }

  return 'uploaded';
}

export function mapDeckToUploadedDeck(
  deck: Deck,
  options: {
    formatFileSize: (size: number) => string;
    formatRelativeUploadDate: (value: string | null | undefined) => string | null;
  }
): UploadedDeckListItem {
  const fileName = deck.file?.filename || `${deck.title}.deck`;

  return {
    id: deck.id,
    name: fileName,
    fileType: inferDeckFileType(fileName),
    fileSizeBytes: typeof deck.file?.size === 'number' ? deck.file.size : null,
    fileKindLabel: inferDeckFileKindLabel(fileName),
    fileSizeLabel: typeof deck.file?.size === 'number' ? options.formatFileSize(deck.file.size) : null,
    uploadedAt: deck.file?.uploadedAt ?? deck.updatedAt,
    uploadedAtLabel: options.formatRelativeUploadDate(deck.file?.uploadedAt ?? deck.updatedAt),
    status: mapDeckStatusToListStatus(deck.status)
  };
}

export function mapWorkspaceDeckRecordToListItem(
  deck: WorkspaceDeckRecord,
  options: {
    formatDeckFileSize: (size: number | null | undefined) => string | null;
    formatDeckUploadDate: (value: string | null | undefined) => string | null;
    selectedDeckId?: string | null;
  }
): UploadedDeckListItem {
  const fileName = deck.originalFilename || deck.displayName || `${deck.id}.deck`;
  const status = options.selectedDeckId && options.selectedDeckId === deck.id ? 'selected' : mapDeckStatusToListStatus(deck.status);

  return {
    id: deck.id,
    name: fileName,
    fileType: deck.fileType || inferDeckFileType(fileName),
    fileSizeBytes: deck.fileSizeBytes,
    fileKindLabel: inferDeckFileKindLabel(fileName),
    fileSizeLabel: options.formatDeckFileSize(deck.fileSizeBytes),
    uploadedAt: deck.updatedAt,
    uploadedAtLabel: options.formatDeckUploadDate(deck.updatedAt),
    status,
    thumbnailUrl: deck.thumbnailUrl ?? null
  };
}

export function inferDeckFileType(name: string): DeckFileType {
  const extension = name.split('.').pop()?.toLowerCase();
  if (extension === 'ppt') return 'ppt';
  if (extension === 'pptx') return 'pptx';
  if (extension === 'pdf') return 'pdf';
  if (extension === 'key') return 'key';
  return 'other';
}

export function inferDeckFileKindLabel(name: string): string {
  const fileType = inferDeckFileType(name);
  if (fileType === 'ppt' || fileType === 'pptx') return 'PPT';
  if (fileType === 'pdf') return 'PDF';
  if (fileType === 'key') return 'KEY';
  return 'FILE';
}
