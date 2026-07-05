import type { SaveConfirmationBannerModel } from '$lib/contracts/types';

export interface UploadedDocumentViewModel {
  name: string;
  sizeLabel: string;
  statusLabel: string;
  statusTone: 'success' | 'info' | 'warning' | 'danger';
  fileKindLabel: string;
}

export type DeckUploadStatus = 'idle' | 'uploading' | 'saved' | 'failed';

export type UploadDeckWidgetState =
  | 'idle'
  | 'drag_active'
  | 'selected'
  | 'uploading'
  | 'uploaded'
  | 'processing'
  | 'ready'
  | 'failed';

export interface UploadDeckWidgetViewModel {
  state: UploadDeckWidgetState;
  title: string;
  supportCopy: string;
  instruction: string;
  acceptedFormatsLabel: string;
  browseLabel: string;
  showUploadedDocument: boolean;
  uploadedDocument: UploadedDocumentViewModel | null;
  confirmation: SaveConfirmationBannerModel | null;
  helperLabel: string;
  helperHrefLabel: string;
  helperHref: string;
  primaryActionLabel: string | null;
  primaryActionEnabled: boolean;
}

export function buildUploadDeckWidgetViewModel(input: {
  deckFile: File | null;
  deckDragActive: boolean;
  deckUploadStatus: DeckUploadStatus;
  deckExtractionStatus: 'idle' | 'queued' | 'processing' | 'ready' | 'failed';
  uploadError: string;
  saveConfirmation: SaveConfirmationBannerModel | null;
  canContinueAfterUpload: boolean;
  buttonLabel: string;
  maxFileLabel: string;
  formatFileSize: (size: number) => string;
}): UploadDeckWidgetViewModel {
  function resolveWidgetState(localInput: {
    deckFile: File | null;
    deckDragActive: boolean;
    deckUploadStatus: DeckUploadStatus;
    deckExtractionStatus: 'idle' | 'queued' | 'processing' | 'ready' | 'failed';
    uploadError: string;
  }): UploadDeckWidgetState {
    if (localInput.deckUploadStatus === 'failed' || localInput.uploadError) return 'failed';
    if (localInput.deckDragActive && !localInput.deckFile) return 'drag_active';
    if (localInput.deckUploadStatus === 'uploading') return 'uploading';
    if (localInput.deckUploadStatus === 'saved' && localInput.deckExtractionStatus === 'ready') return 'ready';
    if (localInput.deckUploadStatus === 'saved' && localInput.deckExtractionStatus === 'processing') return 'processing';
    if (localInput.deckUploadStatus === 'saved' && localInput.deckExtractionStatus === 'queued') return 'uploaded';
    if (localInput.deckUploadStatus === 'saved' && localInput.deckExtractionStatus === 'failed') return 'uploaded';
    if (localInput.deckFile) return 'selected';
    return 'idle';
  }

  function resolveRowStatusLabel(state: UploadDeckWidgetState): string {
    if (state === 'ready' || state === 'uploaded') return 'Uploaded';
    if (state === 'processing') return 'Processing';
    if (state === 'uploading' || state === 'selected') return 'Saving';
    if (state === 'failed') return 'Failed';
    return 'Selected';
  }

  function resolveRowStatusTone(state: UploadDeckWidgetState): UploadedDocumentViewModel['statusTone'] {
    if (state === 'failed') return 'danger';
    if (state === 'processing' || state === 'uploading' || state === 'selected') return 'info';
    return 'success';
  }

  function resolveFileKindLabel(fileName: string): string {
    const extension = fileName.split('.').pop()?.toUpperCase();
    if (extension === 'PPT' || extension === 'PPTX') return 'PPT';
    if (extension === 'PDF') return 'PDF';
    if (extension === 'KEY') return 'KEY';
    return 'FILE';
  }

  function resolveConfirmation(
    state: UploadDeckWidgetState,
    confirmation: SaveConfirmationBannerModel | null,
    uploadError: string
  ): SaveConfirmationBannerModel | null {
    if (confirmation) return confirmation;
    if (state === 'failed') {
      return {
        title: 'Deck save failed',
        message: uploadError || 'Try the upload again or choose a different source file.',
        tone: 'danger'
      };
    }
    if (state === 'processing') {
      return {
        title: 'Deck uploaded',
        message: 'The backend worker pipeline will continue processing from workflow-state.',
        tone: 'info'
      };
    }
    if (state === 'uploaded') {
      return {
        title: 'Deck uploaded',
        message: 'Your deck is saved. The backend worker pipeline will continue from workflow-state.',
        tone: 'success'
      };
    }
    return null;
  }

  const state = resolveWidgetState(input);
  const uploadedDocument = input.deckFile
    ? {
        name: input.deckFile.name,
        sizeLabel: input.formatFileSize(input.deckFile.size),
        statusLabel: resolveRowStatusLabel(state),
        statusTone: resolveRowStatusTone(state),
        fileKindLabel: resolveFileKindLabel(input.deckFile.name)
      }
    : null;

  return {
    state,
    title: 'Upload your deck',
    supportCopy: "Upload a PDF or PowerPoint file. We'll save the original first, then the backend worker pipeline continues from workflow-state.",
    instruction: state === 'drag_active' ? 'Drop your file here' : 'Drag and drop your file here',
    acceptedFormatsLabel: input.maxFileLabel,
    browseLabel: 'browse files',
    showUploadedDocument: Boolean(uploadedDocument),
    uploadedDocument,
    confirmation: resolveConfirmation(state, input.saveConfirmation, input.uploadError),
    helperLabel: state === 'uploaded' ? 'File saved. Next step:' : 'Having issues uploading? Try our',
    helperHrefLabel: state === 'uploaded' ? '' : 'help guide',
    helperHref: state === 'uploaded' ? '#' : '/help',
    primaryActionLabel: input.canContinueAfterUpload ? input.buttonLabel : null,
    primaryActionEnabled: input.canContinueAfterUpload
  };
}
