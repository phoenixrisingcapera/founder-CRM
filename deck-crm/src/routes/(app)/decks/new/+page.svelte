<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { deckProductApiPath } from '$lib/contracts';
  import type { SaveConfirmation } from '@deck-aistack-codes/shared';
import AppShell from '$components/AppShell.svelte';
import DeckLoaderOverlay from '$components/DeckLoaderOverlay.svelte';
import UploadDeck from '$components/UploadDeck.svelte';
import { readApiJsonOrThrow, toApiErrorBannerModel, type ApiErrorBannerModel } from '$lib/api/apiError';
  import type {
    WorkspaceDeckRecord,
    UploadedDeckListItem
  } from '$lib/components/deckService/upload/uploaded-decks-list.types';
  import { mapWorkspaceDeckRecordToListItem } from '$lib/components/deckService/upload/uploaded-decks-list.types';
  import type { SaveConfirmationBannerModel } from '$lib/contracts/types';
  import BrandLoader from '$lib/components/deckService/brand/BrandLoader.svelte';
  import BrandProfileCard from '$lib/components/deckService/brand/BrandProfileCard.svelte';
  import {
    getDeckWorkflowStatus,
    type SmartDeckProcessingStatus,
    type DeckExtractionStatus,
    type WorkflowSourceAsset,
    type WorkflowSourceSlide
  } from '$lib/api/deckService/workflow.client';
  import type { DeckUploadStatus } from '$lib/components/deckService/upload/upload-deck.types';
  import { deckServiceClient } from '$lib/api/deckServiceClient';
  import { normalizeSaveConfirmation } from '$lib/utils/saveConfirmation';
  import { hasBrandSignals, type BrandGuidelinesStatus, type BrandProfile, type BrandStatus } from '$lib/types/deckService-brand';
  type DeckUploadStage = 'creating' | 'requesting_upload' | 'uploading' | 'confirming' | 'processing' | 'ready';
  type FirstBatchSourceType = 'url_branding' | 'logo_branding';
  type FirstBatchReceipt = {
    deckId: string;
    batchId: string;
    sourceType: FirstBatchSourceType;
    nextUrl?: string | null;
    confirmation?: SaveConfirmation | null;
  };
  type DeckUploadSession = {
    acceptedFileTypes: string[];
    maxFileSizeBytes: number | null;
  };
  type UploadErrorPayload = {
    message?: unknown;
    detail?: unknown;
    error?: unknown;
    requestId?: unknown;
  };
  type ExtractBrandResponse = {
    brandProfile: BrandProfile | null;
  };
  type UpdateBrandProfileResponse = {
    brandProfile: BrandProfile | null;
  };
  type WorkspaceDecksState = {
    decks: WorkspaceDeckRecord[];
    isLoading: boolean;
    error: string | null;
    errorBanner: ApiErrorBannerModel | null;
    selectedDeckId: string | null;
  };

  const acceptedDeckTypes =
    '.pdf,.ppt,.pptx,application/pdf,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation';
  const acceptedLogoTypes = '.png,.jpg,.jpeg,.gif,.webp,image/png,image/jpeg,image/gif,image/webp';
  const acceptedGuidelineTypes =
    '.pdf,.doc,.docx,.md,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/markdown,text/plain';

  const firstBatchMode = $derived.by(() => {
    const mode = page.url.searchParams.get('firstBatch');
    if (mode === 'url_branding' || mode === 'logo_branding' || mode === 'supporting_context') return mode;
    return 'slide_miniatures';
  });
  const showHeroStepper = false;

  let deckFile = $state<File | null>(null);
  let deckId = $state('');
  let deck_upload_status = $state<DeckUploadStatus>('idle');
  let deckSourceFileStatus = $state('');
  let deckOriginalFileUrl = $state('');
  let deck_extraction_status = $state<DeckExtractionStatus>('idle');
  let deckStatusSteps = $state<Array<{ key: string; label: string; status: string }>>([]);
  let uploadProgress = $state(0);
  let uploadError = $state('');
  let deckUploadStage = $state<DeckUploadStage | 'idle' | 'failed'>('idle');
  let deckDragActive = $state(false);
  let deckStatusSummary = $state('');
  let uploadConfirmation = $state<SaveConfirmation | null>(null);
  const workspaceDecksState = $state<WorkspaceDecksState>({
    decks: [],
    isLoading: true,
    error: null,
    errorBanner: null,
    selectedDeckId: null
  });
  let workspaceDecksLoadInFlight: Promise<void> | null = null;
  let workspaceDecksLastLoadedAt = 0;
  let persistedSourceSlides = $state<WorkflowSourceSlide[]>([]);
  let persistedSourceLoading = $state(false);
  let persistedSourceError = $state('');
  let latestProcessingStatus = $state<SmartDeckProcessingStatus | null>(null);
  let deckLoaderTransitioning = $state(false);
  let lastWorkspaceDeckStatusKey = '';

  let companyUrl = $state('');
  let logoFile = $state<File | null>(null);
  let brandGuidelinesFile = $state<File | null>(null);
  let logoDragActive = $state(false);
  let guidelinesDragActive = $state(false);
  let brand_status = $state<BrandStatus>('idle');
  let brandGuidelinesStatus = $state<BrandGuidelinesStatus>('idle');
  let brandError = $state('');
  let brandApproved = $state(false);
  let brandProfile = $state<BrandProfile | null>(null);
  let brandModalOpen = $state(false);
  let editingBrand = $state(false);
  let savingBrand = $state(false);
  let brandSaveError = $state('');
  let localLogoPreviewUrl = $state('');
  let autoBrandExtractionDecks = new Set<string>();
  let brandExtractionInFlightDecks = new Set<string>();

  function formatFileSize(size: number) {
    return formatDeckFileSize(size) ?? '0 KB';
  }

  function formatDeckFileSize(size: number | null | undefined): string | null {
    if (typeof size !== 'number' || Number.isNaN(size) || size <= 0) return null;
    if (size < 1024 * 1024) {
      return `${Math.max(1, Math.round(size / 1024))} KB`;
    }

    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  function formatDeckUploadDate(value: string | null | undefined): string | null {
    if (!value) return null;

    const timestamp = new Date(value).getTime();
    if (Number.isNaN(timestamp)) return null;

    const deltaSeconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
    if (deltaSeconds < 60) return 'Just now';

    const deltaMinutes = Math.round(deltaSeconds / 60);
    if (deltaMinutes < 60) return `${deltaMinutes}m ago`;

    const deltaHours = Math.round(deltaMinutes / 60);
    if (deltaHours < 24) return `${deltaHours}h ago`;

    const deltaDays = Math.round(deltaHours / 24);
    if (deltaDays < 7) return `${deltaDays}d ago`;

    return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(new Date(timestamp));
  }

  const workspaceDecks = $derived.by<UploadedDeckListItem[]>(() =>
    workspaceDecksState.decks.map((deck) =>
      mapWorkspaceDeckRecordToListItem(deck, {
        formatDeckFileSize,
        formatDeckUploadDate,
        selectedDeckId: deck.id === deckId ? deckId : workspaceDecksState.selectedDeckId
      })
    )
  );

  const workspaceDecksLoading = $derived(workspaceDecksState.isLoading);

  async function softRemoveDeckFromBackend(deckId: string) {
    const path = deckProductApiPath(`/decks/${deckId}/soft-delete`);
    const response = await fetch(path, { method: 'POST' });
    await readApiJsonOrThrow(response, 'Could not remove this deck.', path);
  }

  async function cleanupBrokenIntakeDecks(currentDeckIds: string[], reason = 'successful_intake_cleanup') {
    if (currentDeckIds.length === 0) return;

    const path = deckProductApiPath('/decks/intake-cleanup');
    try {
      await fetch(path, {
        method: 'POST',
        headers: {
          'content-type': 'application/json'
        },
        body: JSON.stringify({
          currentDeckIds,
          reason
        })
      });
    } catch {
      // Cleanup is intentionally silent. Stale rows should not block the current intake run.
    }
  }

  async function loadWorkspaceDecks(showLoading = false) {
    const state = workspaceDecksState;
    const minIntervalMs = showLoading ? 0 : 8000;
    const now = Date.now();

    if (!showLoading && state.decks.length > 0 && workspaceDecksLastLoadedAt > 0 && now - workspaceDecksLastLoadedAt < minIntervalMs) {
      return;
    }
    if (workspaceDecksLoadInFlight) {
      await workspaceDecksLoadInFlight;
      return;
    }

    const request = (async () => {
      if (showLoading) state.isLoading = true;
      state.error = null;
      state.errorBanner = null;

      try {
        const response = await fetch(deckProductApiPath('/decks'));
        const payload = await readApiJsonOrThrow<{ decks?: WorkspaceDeckRecord[] }>(
          response,
          'Could not load uploaded decks.',
          deckProductApiPath('/decks')
        );

        const decks = Array.isArray(payload?.decks) ? payload.decks : [];
        state.decks = decks;
        if (state.selectedDeckId && !decks.some((deck) => deck.id === state.selectedDeckId)) {
          state.selectedDeckId = null;
        }
        workspaceDecksLastLoadedAt = Date.now();
      } catch (error) {
        const banner = toApiErrorBannerModel(error, 'Could not load uploaded decks.');
        if (state.decks.length === 0) {
          state.decks = [];
        }
        state.error = banner.message;
        state.errorBanner = banner;
      } finally {
        if (showLoading) state.isLoading = false;
        workspaceDecksLoadInFlight = null;
      }
    })();

    workspaceDecksLoadInFlight = request;
    await request;
  }

  async function retryWorkspaceDeck(deckId: string) {
    const response = await fetch(deckProductApiPath(`/decks/${deckId}/retry`), { method: 'POST' });
    const payload = await readApiJsonOrThrow(response, 'Could not retry this deck.', deckProductApiPath(`/decks/${deckId}/retry`));

    await loadWorkspaceDecks(true);
    return payload;
  }

  async function removeWorkspaceDeck(deckId: string) {
    const previousDecks = [...workspaceDecksState.decks];
    const previousSelectedDeckId = workspaceDecksState.selectedDeckId;
    workspaceDecksState.error = null;
    workspaceDecksState.errorBanner = null;
    workspaceDecksState.decks = workspaceDecksState.decks.filter((deck) => deck.id !== deckId);
    if (workspaceDecksState.selectedDeckId === deckId) {
      workspaceDecksState.selectedDeckId = null;
    }

    try {
      await softRemoveDeckFromBackend(deckId);
      await loadWorkspaceDecks(true);
      return { ok: true };
    } catch (error) {
      const banner = toApiErrorBannerModel(error, 'Could not remove this deck.');
      workspaceDecksState.decks = previousDecks;
      workspaceDecksState.selectedDeckId = previousSelectedDeckId;
      workspaceDecksState.error = banner.message;
      workspaceDecksState.errorBanner = banner;
      return null;
    }
  }

  async function extractDeckBrand({
    deckId,
    companyUrl,
    logoFile,
    brandGuidelinesFile
  }: {
    deckId: string;
    companyUrl: string;
    logoFile: File | null;
    brandGuidelinesFile?: File | null;
  }): Promise<ExtractBrandResponse> {
    const formData = new FormData();
    if (companyUrl.trim()) {
      formData.set('companyUrl', companyUrl.trim());
    }
    if (logoFile) {
      formData.set('logoFile', logoFile);
    }
    if (brandGuidelinesFile) {
      formData.set('brandGuidelinesFile', brandGuidelinesFile);
    }

    const path = deckProductApiPath(`/decks/${deckId}/workflows/brand-extraction`);
    const response = await fetch(path, {
      method: 'POST',
      body: formData
    });

    return readApiJsonOrThrow<ExtractBrandResponse>(response, 'Brand extraction failed.', path);
  }

  async function updateDeckBrandProfile({
    deckId,
    brandProfile
  }: {
    deckId: string;
    brandProfile: Partial<BrandProfile>;
  }): Promise<UpdateBrandProfileResponse> {
    const path = deckProductApiPath(`/decks/${deckId}/brand-profile`);
    const response = await fetch(path, {
      method: 'PATCH',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify(brandProfile)
    });

    return readApiJsonOrThrow<UpdateBrandProfileResponse>(response, 'Brand profile update failed.', path);
  }

  function resetBrandState() {
    if (localLogoPreviewUrl) {
      URL.revokeObjectURL(localLogoPreviewUrl);
      localLogoPreviewUrl = '';
    }
    companyUrl = '';
    logoFile = null;
    brandGuidelinesFile = null;
    brand_status = 'idle';
    brandGuidelinesStatus = 'idle';
    brandError = '';
    brandApproved = false;
    brandProfile = null;
    editingBrand = false;
    brandSaveError = '';
  }

  function extractUploadErrorMessage(payload: UploadErrorPayload | null, fallback = 'Deck upload failed.') {
    if (!payload || typeof payload !== 'object') return fallback;

    const detail = payload.detail;
    const detailRecord = detail && typeof detail === 'object' ? (detail as Record<string, unknown>) : null;
    const message =
      (typeof payload.message === 'string' && payload.message) ||
      (typeof detail === 'string' && detail) ||
      (typeof detailRecord?.message === 'string' && detailRecord.message) ||
      (typeof detailRecord?.error === 'string' && detailRecord.error) ||
      (typeof payload.error === 'string' && payload.error) ||
      fallback;
    const requestId =
      (typeof payload.requestId === 'string' && payload.requestId) ||
      (typeof detailRecord?.requestId === 'string' && detailRecord.requestId) ||
      '';
    const ticketId = typeof detailRecord?.ticketId === 'string' ? detailRecord.ticketId : '';
    const suffix = [requestId ? `request ${requestId}` : '', ticketId ? `ticket ${ticketId}` : '']
      .filter(Boolean)
      .join(', ');

    return suffix ? `${message} (${suffix})` : message;
  }

  async function loadDeckUploadSession(): Promise<DeckUploadSession> {
    const response = await fetch(deckProductApiPath('/decks/upload-session'), {
      method: 'POST'
    });
    const payload = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(
        typeof payload?.message === 'string'
          ? payload.message
          : typeof payload?.detail === 'string'
            ? payload.detail
            : 'Could not prepare the deck upload session.'
      );
    }

    const acceptedFileTypes = Array.isArray(payload?.acceptedFileTypes)
      ? payload.acceptedFileTypes
      : Array.isArray(payload?.accepted_file_types)
        ? payload.accepted_file_types
        : ['pdf', 'ppt', 'pptx'];

    return {
      acceptedFileTypes: acceptedFileTypes.map((value: unknown) => String(value).replace(/^\./, '').toLowerCase()),
      maxFileSizeBytes:
        typeof payload?.maxFileSizeBytes === 'number'
          ? payload.maxFileSizeBytes
          : typeof payload?.max_file_size_bytes === 'number'
            ? payload.max_file_size_bytes
            : null
    };
  }

  function validateDeckFileForSession(file: File, session: DeckUploadSession) {
    if (session.maxFileSizeBytes && file.size > session.maxFileSizeBytes) {
      throw new Error(`Deck upload is limited to ${formatFileSize(session.maxFileSizeBytes)}.`);
    }

    const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (session.acceptedFileTypes.length > 0 && !session.acceptedFileTypes.includes(extension)) {
      throw new Error(`Upload a ${session.acceptedFileTypes.map((type) => type.toUpperCase()).join(', ')} deck file.`);
    }
  }

  function formatUploadStageLabel(stage: DeckUploadStage | 'idle' | 'failed') {
    switch (stage) {
      case 'creating':
        return 'Creating deck';
      case 'requesting_upload':
        return 'Preparing upload';
      case 'uploading':
        return 'Uploading file';
      case 'confirming':
        return 'Confirming upload';
      case 'processing':
        return 'Processing deck';
      case 'ready':
        return 'Ready';
      case 'failed':
        return 'Failed';
      default:
        return 'Starting';
    }
  }

  async function saveDeck(file: File) {
    deck_upload_status = 'uploading';
    deck_extraction_status = 'queued';
    deckStatusSteps = [];
    uploadProgress = 18;
    uploadError = '';
    deckUploadStage = 'creating';
    deckStatusSummary = '';
    deckId = '';
    deckSourceFileStatus = '';
    deckOriginalFileUrl = '';
    uploadConfirmation = null;
    persistedSourceSlides = [];
    persistedSourceLoading = false;
    persistedSourceError = '';
    brandModalOpen = false;
    resetBrandState();

    try {
      const result = await deckServiceClient.uploadFirstDeck(
        file,
        {
          audience: 'Investment Committee',
          purpose: 'Initial diligence review'
        },
        {
          onStage: (stage) => {
            deckUploadStage = stage;
            if (stage === 'uploading') uploadProgress = 48;
            if (stage === 'confirming') uploadProgress = 72;
            if (stage === 'processing') uploadProgress = 88;
            if (stage === 'ready') uploadProgress = 96;
          }
        }
      );

      const nextDeckId = String(result.deckId ?? '');
      if (!nextDeckId) {
        throw new Error('Deck upload finished without a persisted deck id.');
      }

      deckId = nextDeckId;
      lastWorkspaceDeckStatusKey = '';
      deck_upload_status = 'saved';
      deckSourceFileStatus = 'ready';
      deckOriginalFileUrl = '';
      deck_extraction_status = 'queued';
      uploadConfirmation = null;
      uploadProgress = 100;
      deckUploadStage = 'ready';
      brandModalOpen = true;
      await cleanupBrokenIntakeDecks([nextDeckId], 'successful_upload_cleanup');
      await loadWorkspaceDecks();
      void refreshDeckStatus(nextDeckId);
      void refreshBrandProfile(nextDeckId);
    } catch (error) {
      deck_upload_status = 'failed';
      deck_extraction_status = 'failed';
      deckUploadStage = 'failed';
      uploadProgress = 0;
      uploadError = error instanceof Error ? error.message : 'Deck upload failed.';
    }
  }

  async function createSourceFirstBatch(sourceType: FirstBatchSourceType) {
    const formData = new FormData();
    formData.set('sourceType', sourceType);
    if (companyUrl.trim()) formData.set('websiteUrl', companyUrl.trim());
    if (logoFile) formData.set('logoFile', logoFile);

    const response = await fetch(deckProductApiPath('/decks/first-batch'), {
      method: 'POST',
      body: formData
    });

    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(typeof payload?.message === 'string' ? payload.message : 'First version creation failed.');
    }

    const receiptPayload = (payload && typeof payload === 'object' ? payload : null) as Record<string, unknown> | null;
    const receipt: FirstBatchReceipt = {
      deckId: String(receiptPayload?.deckId ?? ''),
      batchId: String(receiptPayload?.batchId ?? ''),
      sourceType: receiptPayload?.sourceType === 'logo_branding' ? 'logo_branding' : 'url_branding',
      nextUrl: typeof receiptPayload?.nextUrl === 'string' ? receiptPayload.nextUrl : null,
      confirmation: normalizeSaveConfirmation(receiptPayload?.confirmation as Record<string, unknown> | null | undefined, 'deck_properties_saved')
    };
    if (!receipt.deckId || !receipt.batchId) {
      throw new Error('First version finished without a persisted deck receipt.');
    }

    deckId = receipt.deckId;
    lastWorkspaceDeckStatusKey = '';
    deck_upload_status = 'saved';
    deckSourceFileStatus = 'saved';
    deckOriginalFileUrl = receipt.sourceType;
    deck_extraction_status = 'ready';
    uploadConfirmation = receipt.confirmation ?? null;
    uploadProgress = 100;
    await cleanupBrokenIntakeDecks([receipt.deckId], 'successful_first_batch_cleanup');
    await loadWorkspaceDecks();
    void refreshPersistedSourceInspection(receipt.deckId);
    return receipt;
  }

  async function refreshDeckStatus(nextDeckId: string) {
    try {
      const status = await getDeckWorkflowStatus(nextDeckId);
      latestProcessingStatus = status;
      const brandStatusValue = status.brandProfile?.status ?? brand_status;
      const nextDeckUploadStatus =
        status.sourceFileSaved
          ? 'saved'
          : status.status === 'failed'
            ? 'failed'
            : status.status === 'processing'
              ? 'uploading'
              : 'idle';
      const nextWorkspaceDeckStatusKey = JSON.stringify({
        uploadStatus: nextDeckUploadStatus,
        deckExtractionStatus: status.deckExtractionStatus,
        sourceFileStatus: status.sourceFileStatus ?? (status.sourceFileSaved ? 'saved' : ''),
        brandStatus: brandStatusValue
      });

      deck_upload_status = nextDeckUploadStatus;
      deckSourceFileStatus = status.sourceFileStatus ?? (status.sourceFileSaved ? 'saved' : deckSourceFileStatus);
      deck_extraction_status = status.deckExtractionStatus;
      deckStatusSummary = status.message ?? '';
      deckStatusSteps = status.phases.map((phase) => ({
        key: phase.key,
        label: phase.label,
        status: phase.status
      }));
      if (status.latestConfirmation) {
        uploadConfirmation = normalizeSaveConfirmation(status.latestConfirmation, 'deck_upload_saved');
      }
      if (brandStatusValue === 'ready' || brandStatusValue === 'extracting' || brandStatusValue === 'failed' || brandStatusValue === 'idle') {
        brand_status = brandStatusValue as BrandStatus;
      }

      if (nextWorkspaceDeckStatusKey !== lastWorkspaceDeckStatusKey) {
        lastWorkspaceDeckStatusKey = nextWorkspaceDeckStatusKey;
        await loadWorkspaceDecks();
      }
    } catch (error) {
      if (deck_upload_status === 'saved') {
        deckStatusSummary = 'Deck is saved. Processing status is still syncing.';
        return;
      }
    }
  }

  async function refreshBrandProfile(nextDeckId: string) {
    try {
      const status = latestProcessingStatus ?? (await getDeckWorkflowStatus(nextDeckId));
      const persistedProfile = status.brandProfile ?? null;
      if (persistedProfile) {
        brandProfile = persistedProfile;
        if (persistedProfile.brandGuidelinesStatus) {
          brandGuidelinesStatus = persistedProfile.brandGuidelinesStatus;
        }

        if (
          persistedProfile.status === 'ready' ||
          persistedProfile.status === 'extracting' ||
          persistedProfile.status === 'failed'
        ) {
          brand_status = persistedProfile.status;
        } else {
          brand_status = 'idle';
        }
        autoBrandExtractionDecks.delete(nextDeckId);
        return;
      }
    } catch {
      return;
    }

    if (!hasBrandSourceInput && deck_extraction_status !== 'ready') {
      brand_status = 'idle';
      brandError = '';
      autoBrandExtractionDecks.delete(nextDeckId);
      return;
    }

    if (!deckId && !deckUploadComplete && !hasBrandSourceInput) {
      return;
    }

    if (brandExtractionInFlightDecks.has(nextDeckId) || autoBrandExtractionDecks.has(nextDeckId)) {
      return;
    }

    brandExtractionInFlightDecks.add(nextDeckId);
    brand_status = 'extracting';
    brandError = '';
    try {
      const deckOnlyExtraction = !companyUrl.trim() && !logoFile && !brandGuidelinesFile;
      const payload = await extractDeckBrand({
        deckId: nextDeckId,
        companyUrl: deckOnlyExtraction ? '' : companyUrl.trim(),
        logoFile: deckOnlyExtraction ? null : logoFile,
        brandGuidelinesFile: deckOnlyExtraction ? null : brandGuidelinesFile
      });

      brandProfile = payload?.brandProfile ?? null;
      brand_status =
        payload?.brandProfile?.status === 'ready'
          ? 'ready'
          : payload?.brandProfile?.status === 'failed'
            ? 'failed'
            : 'extracting';
      if (payload?.brandProfile?.brandGuidelinesStatus) {
        brandGuidelinesStatus = payload.brandProfile.brandGuidelinesStatus;
      }
      autoBrandExtractionDecks.add(nextDeckId);
    } catch (error) {
      brand_status = 'failed';
      brandError = error instanceof Error ? error.message : 'Brand extraction failed.';
      if (brandGuidelinesFile) {
        brandGuidelinesStatus = 'failed';
      }
    } finally {
      brandExtractionInFlightDecks.delete(nextDeckId);
    }
  }

  async function refreshPersistedSourceInspection(nextDeckId: string) {
    persistedSourceLoading = true;
    persistedSourceError = '';

    try {
      const status = latestProcessingStatus ?? (await getDeckWorkflowStatus(nextDeckId));
      persistedSourceSlides = status.sourceSlides ?? [];
    } catch (error) {
      persistedSourceError =
        error instanceof Error ? error.message : 'Could not load the persisted source summary.';
    } finally {
      persistedSourceLoading = false;
    }
  }

  $effect(() => {
    if (deck_upload_status !== 'uploading') {
      return;
    }

    if (uploadProgress < 22) {
      uploadProgress = 22;
    }

    const timer = window.setInterval(() => {
      uploadProgress = Math.min(36, uploadProgress + Math.max(2, Math.round((40 - uploadProgress) / 5)));
    }, 420);

    return () => {
      window.clearInterval(timer);
    };
  });

  $effect(() => {
    if (!deckId || deck_upload_status !== 'saved' || deck_extraction_status === 'ready' || deck_extraction_status === 'failed') {
      return;
    }

    const timer = window.setInterval(() => {
      void refreshDeckStatus(deckId);
    }, 3000);

    return () => {
      window.clearInterval(timer);
    };
  });

  $effect(() => {
    if (!deckId || deck_upload_status !== 'saved' || deck_extraction_status !== 'ready') {
      return;
    }

    if (persistedSourceLoading) {
      return;
    }

    void refreshPersistedSourceInspection(deckId);
  });

  $effect(() => {
    if (!deckId || deck_upload_status !== 'saved' || deck_extraction_status === 'ready' || deck_extraction_status === 'failed') {
      return;
    }

    const timer = window.setInterval(() => {
      uploadProgress = Math.min(92, uploadProgress + Math.max(1, Math.round((94 - uploadProgress) / 8)));
    }, 900);

    return () => {
      window.clearInterval(timer);
    };
  });

  $effect(() => {
    if (!deckId || deck_upload_status !== 'saved') {
      return;
    }

    const shouldPollBrand = brandModalOpen || brand_status === 'extracting' || brand_status === 'idle';
    if (!shouldPollBrand) {
      return;
    }

    const timer = window.setInterval(() => {
      void refreshBrandProfile(deckId);
    }, 2500);

    return () => {
      window.clearInterval(timer);
    };
  });

  async function handleDeckSelection(event: Event) {
    const target = event.currentTarget as HTMLInputElement;
    const file = target.files?.[0] ?? null;
    await handleDeckFile(file);
  }

  async function handleDeckFile(file: File | null) {
    deckFile = file;
    deckDragActive = false;

    if (file) {
      await saveDeck(file);
    }
  }

  function handleDeckDragEvent(event: DragEvent) {
    event.preventDefault();
    deckDragActive = true;
  }

  function handleDeckDragLeave(event: DragEvent) {
    event.preventDefault();
    deckDragActive = false;
  }

  async function handleDeckDrop(event: DragEvent) {
    event.preventDefault();
    const file = event.dataTransfer?.files?.[0] ?? null;
    await handleDeckFile(file);
  }

  function handleLogoDragEvent(event: DragEvent) {
    event.preventDefault();
    logoDragActive = true;
  }

  function handleLogoDragLeave(event: DragEvent) {
    event.preventDefault();
    logoDragActive = false;
  }

  function handleGuidelinesDragEvent(event: DragEvent) {
    event.preventDefault();
    guidelinesDragActive = true;
  }

  function handleGuidelinesDragLeave(event: DragEvent) {
    event.preventDefault();
    guidelinesDragActive = false;
  }

  async function handleLogoFile(file: File | null) {
    logoFile = file;
    logoDragActive = false;
    brandApproved = false;
    brandError = '';
    brandProfile = null;
    brand_status = 'idle';

    if (localLogoPreviewUrl) {
      URL.revokeObjectURL(localLogoPreviewUrl);
      localLogoPreviewUrl = '';
    }

    if (!file) {
      if (!companyUrl.trim() && !brandGuidelinesFile) {
        brandProfile = null;
        brand_status = 'idle';
      }
      return;
    }

    localLogoPreviewUrl = URL.createObjectURL(file);
  }

  async function handleGuidelinesFile(file: File | null) {
    brandGuidelinesFile = file;
    guidelinesDragActive = false;
    brandGuidelinesStatus = file ? 'uploaded' : 'idle';
    brandApproved = false;
    brandProfile = null;
    brand_status = 'idle';
  }

  async function handleLogoDrop(event: DragEvent) {
    event.preventDefault();
    const file = event.dataTransfer?.files?.[0] ?? null;
    await handleLogoFile(file);
  }

  async function handleGuidelinesDrop(event: DragEvent) {
    event.preventDefault();
    const file = event.dataTransfer?.files?.[0] ?? null;
    await handleGuidelinesFile(file);
  }

  function handleCompanyUrlChange(value: string) {
    companyUrl = value;
    brandApproved = false;
    brandProfile = null;
    brand_status = 'idle';
  }

  async function extractBrand() {
    if (!deckUploadComplete && !companyUrl.trim() && !logoFile && !brandGuidelinesFile) {
      return;
    }

    brand_status = 'extracting';
    brandError = '';
    brandApproved = false;
    editingBrand = false;
    brandSaveError = '';
    if (brandGuidelinesFile) {
      brandGuidelinesStatus = 'processing';
    }

    try {
      let targetDeckId = deckId;

      if (!targetDeckId) {
        if (logoFile) {
          const receipt = await createSourceFirstBatch('logo_branding');
          targetDeckId = receipt.deckId;
        } else if (companyUrl.trim()) {
          const receipt = await createSourceFirstBatch('url_branding');
          targetDeckId = receipt.deckId;
        }
      }

      if (!targetDeckId) {
        throw new Error('Load a company URL, logo, or uploaded deck before extracting brand signals.');
      }

      if (!deckUploadComplete && targetDeckId === deckId) {
        throw new Error('Wait for the deck upload receipt before extracting brand signals.');
      }

      if (!hasBrandSourceInput && deck_extraction_status !== 'ready') {
        brand_status = 'idle';
        brandError = '';
        return;
      }

      const payload = await extractDeckBrand({
        deckId: targetDeckId,
        companyUrl,
        logoFile,
        brandGuidelinesFile
      });

      brandProfile = payload?.brandProfile ?? null;
      brand_status =
        payload?.brandProfile?.status === 'ready'
          ? 'ready'
          : payload?.brandProfile?.status === 'failed'
            ? 'failed'
            : 'extracting';
      brandGuidelinesStatus = brandGuidelinesFile ? 'ready' : brandGuidelinesStatus;
      await refreshBrandProfile(deckId);
    } catch (error) {
      brand_status = 'failed';
      brandGuidelinesStatus = brandGuidelinesFile ? 'failed' : brandGuidelinesStatus;
      brandError = error instanceof Error ? error.message : 'Brand extraction failed.';
    }
  }

  async function saveBrandSelection(payload: {
    primaryColor: string;
    secondaryColor: string;
    accentColor: string;
    backgroundColor: string;
    textColor: string;
    visualStyle: string;
    fontCandidates: string[];
  }) {
    if (!brandProfile) {
      return;
    }

    savingBrand = true;
    brandSaveError = '';

    try {
      if (!deckId) {
        throw new Error('Upload or select a deck before saving brand selections so the profile can be persisted.');
      }

      const response = await updateDeckBrandProfile({
        deckId,
        brandProfile: {
          companyName: brandProfile.companyName,
          companyWebsiteUrl: companyUrl || brandProfile.companyWebsiteUrl,
          primaryColor: payload.primaryColor,
          secondaryColor: payload.secondaryColor,
          accentColor: payload.accentColor,
          backgroundColor: payload.backgroundColor,
          textColor: payload.textColor,
          palette: [
            payload.primaryColor,
            payload.secondaryColor,
            payload.accentColor,
            payload.backgroundColor,
            payload.textColor
          ],
          visualStyle: payload.visualStyle,
          fontCandidates: payload.fontCandidates,
          sourceMode: brandProfile.sourceMode ?? brandProfile.source
        }
      });

      brandProfile = response.brandProfile;
      if (
        response.brandProfile?.status === 'ready' ||
        response.brandProfile?.status === 'extracting' ||
        response.brandProfile?.status === 'failed'
      ) {
        brand_status = response.brandProfile.status;
      }
      editingBrand = false;
      brandApproved = true;
    } catch (error) {
      brandSaveError = error instanceof Error ? error.message : 'Brand profile update failed.';
    } finally {
      savingBrand = false;
    }
  }

  async function continueFromBrandReview() {
    brandApproved = true;
    brandModalOpen = false;
    if (deckId) {
      deckLoaderTransitioning = true;
      try {
        const status = await getDeckWorkflowStatus(deckId);
        const canOpenSmartDeck = Boolean(status?.canOpenSmartDeck);
        await goto(
          canOpenSmartDeck ? `/decks/${deckId}/smart-deck` : `/decks/${deckId}/processing`
        );
      } catch (error) {
        deckLoaderTransitioning = false;
        uploadError = error instanceof Error ? error.message : 'Could not open Smart Deck.';
      }
    }
  }

  async function handleExistingDeckSelection(deck: UploadedDeckListItem) {
    if (!deck.id) {
      return;
    }

    workspaceDecksState.selectedDeckId = deck.id;
    deckId = deck.id;

    deckLoaderTransitioning = true;
    try {
      const status = await getDeckWorkflowStatus(deck.id).catch(() => null);
      await goto(
        Boolean(
          status?.canOpenSmartDeck
        )
          ? `/decks/${deck.id}/smart-deck`
          : `/decks/${deck.id}/processing`
      );
    } catch (error) {
      deckLoaderTransitioning = false;
      uploadError = error instanceof Error ? error.message : 'Could not open Smart Deck.';
    }
  }

  const deckUploadComplete = $derived(Boolean(deckId && deck_upload_status === 'saved'));
  const brandStepReady = $derived(Boolean(brandProfile?.id && !brandProfile.id.startsWith('local_brand_') && hasBrandSignals(brandProfile)));
  const hasBrandSourceInput = $derived(companyUrl.trim().length > 0 || Boolean(logoFile) || Boolean(brandGuidelinesFile));
  const canExtractBrand = $derived(brand_status !== 'extracting' && (hasBrandSourceInput || deck_extraction_status === 'ready'));
  const canContinueFromBrandReview = $derived(deckUploadComplete && brandStepReady);
  const canContinueAfterUpload = $derived(deckUploadComplete);
  const deckLoaderOpen = $derived(deck_upload_status === 'uploading' || deckLoaderTransitioning);
  const deckLoaderTitle = $derived.by(() => {
    if (deckLoaderTransitioning) return 'Loading your workspace...';
    return 'Preparing your deck...';
  });
  const deckLoaderSubtitle = $derived.by(() => {
    if (deckLoaderTransitioning) {
      if (deck_extraction_status === 'ready') return 'Opening Smart Deck with the persisted source summary.';
      if (deck_extraction_status === 'failed') return 'Opening Smart Deck with the saved source file and extraction status.';
      return 'Opening Smart Deck while extraction continues in the background.';
    }

    if (deckFile) return `${formatUploadStageLabel(deckUploadStage)} ${deckFile.name} before extraction starts.`;
    return 'Saving the source deck before extraction starts.';
  });
  const deckLoaderStatusLabel = $derived.by(() => {
    if (deckLoaderTransitioning) return 'Opening';
    return formatUploadStageLabel(deckUploadStage);
  });
  const deckLoaderSteps = $derived.by(() => [
    {
      label: 'Create deck',
      status:
        deckUploadStage === 'creating'
          ? 'running'
          : ['requesting_upload', 'uploading', 'confirming', 'processing', 'ready'].includes(deckUploadStage)
            ? 'complete'
            : deck_upload_status === 'failed'
              ? 'failed'
              : 'pending'
    },
    {
      label: 'Upload file',
      status:
        deckUploadStage === 'uploading'
          ? 'running'
          : ['confirming', 'processing', 'ready'].includes(deckUploadStage)
            ? 'complete'
            : deck_upload_status === 'failed'
              ? 'failed'
              : 'pending'
    },
    {
      label: 'Confirm upload',
      status:
        deckUploadStage === 'confirming'
          ? 'running'
          : ['processing', 'ready'].includes(deckUploadStage)
            ? 'complete'
            : deck_upload_status === 'failed'
              ? 'failed'
              : 'pending'
    },
    {
      label: 'Process deck',
      status:
        deckUploadStage === 'processing'
          ? 'running'
          : deckUploadStage === 'ready'
            ? 'complete'
            : deck_upload_status === 'failed'
              ? 'failed'
              : 'pending'
    },
    {
      label: 'Load workspace',
      status: deckLoaderTransitioning ? 'running' : deckUploadStage === 'ready' ? 'complete' : 'pending'
    }
  ] satisfies Array<{ label: string; status: 'pending' | 'running' | 'complete' | 'failed' }>);
  const active_step = $derived.by(() => {
    if (!deckUploadComplete) return 1;
    if (!brandStepReady) return 2;
    return 3;
  });

  const saveConfirmation = $derived.by<SaveConfirmationBannerModel | null>(() => {
    if (deck_upload_status === 'failed') {
      return {
        title: 'Deck save failed',
        message: uploadError || 'Try the upload again or choose a different file.',
        tone: 'danger'
      };
    }

    if (uploadConfirmation) {
      return {
        title: uploadConfirmation.title,
        message: uploadConfirmation.message,
        tone: uploadConfirmation.tone
      };
    }

    return null;
  });

  const stepStates = $derived([
    { label: firstBatchMode === 'slide_miniatures' ? 'Upload deck' : 'Create source version', complete: deckUploadComplete, active: active_step === 1 },
    { label: firstBatchMode === 'logo_branding' ? 'Load logo brand' : firstBatchMode === 'url_branding' ? 'Load URL brand' : 'Load brand', complete: brandStepReady, active: active_step === 2 },
    { label: 'Review brand', complete: brandApproved, active: active_step === 3 },
    { label: 'Choose style', complete: false, active: false },
    { label: 'Create Smart Deck', complete: false, active: false }
  ]);
  const sourceSlides = $derived(persistedSourceSlides.slice(0, 4));
  const sourceMediaAssets = $derived(
    sourceSlides
      .flatMap((slide) =>
        Array.isArray(slide.assets)
          ? slide.assets.map((asset: WorkflowSourceAsset) => ({
              ...asset,
              slideIndex: slide.slideIndex
            }))
          : []
      )
      .filter((asset) => asset.assetType === 'embedded_image' && typeof asset.assetUrl === 'string')
      .slice(0, 4)
  );
  const sourceSlideCount = $derived(sourceSlides.length);

  onMount(() => {
    void loadWorkspaceDecks(true);

    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;

    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';

    return () => {
      if (localLogoPreviewUrl) {
        URL.revokeObjectURL(localLogoPreviewUrl);
      }
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overflow = previousHtmlOverflow;
    };
  });
</script>

<AppShell
  title="Smart Deck Intake"
  subtitle="Create a source-backed first version and keep moving."
  activeNav="upload"
  showTopBar={false}
  showFooterUtilities={true}
  showTopBarCopy={false}
  compactTopBar={true}
  showTopBarSearch={false}
  deckLabel="Smart Deck Intake"
>
  <section class="guided-shell">
    <section class="hero panel">
      <div class="hero-copy">
        <div class="eyebrow">Guided intake</div>
        <h2>Create Smart Deck</h2>
      </div>

      {#if showHeroStepper}
        <ol class="stepper" aria-label="Smart Deck intake steps">
          {#each stepStates as step, index}
            <li class:step-active={step.active} class:step-complete={step.complete}>
              <span class="step-index">{index + 1}</span>
              <span class="step-label">{step.label}</span>
            </li>
          {/each}
        </ol>
      {/if}
    </section>

    <div class="intake-grid">
      <UploadDeck
        accept={acceptedDeckTypes}
        {deckId}
        {deckFile}
        {deckDragActive}
        deckUploadStatus={deck_upload_status}
        deckExtractionStatus={deck_extraction_status}
        {uploadError}
        {saveConfirmation}
        {canContinueAfterUpload}
        {workspaceDecks}
        workspaceDecksLoading={workspaceDecksLoading}
        onDeckSelection={handleDeckSelection}
        onDeckDragEnter={handleDeckDragEvent}
        onDeckDragLeave={handleDeckDragLeave}
        onDeckDrop={handleDeckDrop}
        onSelectDeck={handleExistingDeckSelection}
        onRetryDeck={(targetDeckId) => void retryWorkspaceDeck(targetDeckId)}
        onRemoveDeck={(targetDeckId) => void removeWorkspaceDeck(targetDeckId)}
        onContinue={() => (brandModalOpen = true)}
        {formatFileSize}
      />

      <BrandProfileCard
        {companyUrl}
        {logoFile}
        logoPreviewUrl={localLogoPreviewUrl}
        {logoDragActive}
        {acceptedLogoTypes}
        brandStatus={brand_status}
        brandError={brandError}
        {brandProfile}
        {brandApproved}
        {deckUploadComplete}
        {hasBrandSourceInput}
        {canExtractBrand}
        canContinue={canContinueFromBrandReview}
        modeLabel={firstBatchMode}
        {formatFileSize}
        onCompanyUrlChange={handleCompanyUrlChange}
        onLogoDragEnter={handleLogoDragEvent}
        onLogoDragLeave={handleLogoDragLeave}
        onLogoDrop={handleLogoDrop}
        onLogoFileChange={handleLogoFile}
        onExtract={extractBrand}
        onReview={() => (brandModalOpen = true)}
        onContinue={continueFromBrandReview}
      />
    </div>

    {#if deckId && deck_upload_status === 'saved'}
      <section class="panel source-inspection" aria-label="Persisted source summary">
        <div class="source-summary">
          <div>
            <div class="eyebrow">Persisted source</div>
            <h3>Saved intake workspace</h3>
          </div>
          <span>
            {#if persistedSourceLoading}
              Loading summary...
            {:else if deck_extraction_status === 'ready'}
              {sourceSlideCount} slides
            {:else}
              Waiting for extraction
            {/if}
          </span>
        </div>

        {#if persistedSourceError}
          <p class="muted source-inspection__message">{persistedSourceError}</p>
        {:else if deck_extraction_status !== 'ready'}
          <p class="muted source-inspection__message">
            The deck is saved. Slide structure and embedded media previews will appear here when extraction finishes.
          </p>
        {:else if sourceSlides.length > 0}
          <div class="source-inspection__body">
            <div class="source-slide-list">
              {#each sourceSlides as slide}
                <article>
                  <strong>{slide.slideIndex}. {slide.title}</strong>
                  <small>{slide.blocks?.length ?? 0} blocks · {slide.assets?.length ?? 0} assets</small>
                </article>
              {/each}
            </div>

            {#if sourceMediaAssets.length > 0}
              <div class="media-list" aria-label="Persisted embedded media assets">
                {#each sourceMediaAssets as asset}
                  <a href={asset.assetUrl} target="_blank" rel="noreferrer">
                    <span>{asset.label ?? 'Embedded image'}</span>
                    <small>Slide {asset.slideIndex} · {asset.mimeType ?? 'image'}</small>
                  </a>
                {/each}
              </div>
            {/if}
          </div>
        {:else}
          <p class="muted source-inspection__message">
            Extraction completed, but there is no persisted slide summary to render yet.
          </p>
        {/if}
      </section>
    {/if}
  </section>

  {#if brandModalOpen}
    <BrandLoader
      openAsModal={true}
      modalTitle={brandStepReady ? 'Review your brand' : 'Load your brand'}
      modalSubtitle="Website, logo, and guidelines all feed the same brand profile while deck extraction continues in the background."
      {companyUrl}
      {logoFile}
      logoPreviewUrl={localLogoPreviewUrl}
      {brandGuidelinesFile}
      {logoDragActive}
      {guidelinesDragActive}
      {acceptedLogoTypes}
      {acceptedGuidelineTypes}
      brandStatus={brand_status}
      deckExtractionStatus={deck_extraction_status}
      {brandGuidelinesStatus}
      brandError={brandError}
      {brandProfile}
      {brandApproved}
      {editingBrand}
      {savingBrand}
      brandSaveError={brandSaveError}
      {canExtractBrand}
      canContinue={canContinueFromBrandReview}
      {formatFileSize}
      onCompanyUrlChange={(value) => {
        companyUrl = value;
        brandApproved = false;
        brandProfile = null;
        brand_status = 'idle';
      }}
      onLogoDragEnter={handleLogoDragEvent}
      onLogoDragLeave={handleLogoDragLeave}
      onLogoDrop={handleLogoDrop}
      onLogoFileChange={handleLogoFile}
      onGuidelinesDragEnter={handleGuidelinesDragEvent}
      onGuidelinesDragLeave={handleGuidelinesDragLeave}
      onGuidelinesDrop={handleGuidelinesDrop}
      onGuidelinesFileChange={handleGuidelinesFile}
      onExtract={extractBrand}
      onEdit={() => {
        editingBrand = !editingBrand;
        brandApproved = false;
        brandSaveError = '';
      }}
      onApprove={() => (brandApproved = true)}
      onContinue={continueFromBrandReview}
      onClose={() => (brandModalOpen = false)}
      onSaveBrand={saveBrandSelection}
    />
  {/if}

  <DeckLoaderOverlay
    open={deckLoaderOpen}
    title={deckLoaderTitle}
    subtitle={deckLoaderSubtitle}
    statusLabel={deckLoaderStatusLabel}
    progress={deckLoaderTransitioning ? Math.max(uploadProgress, 92) : uploadProgress}
    steps={deckLoaderSteps}
    errorMessage={deck_upload_status === 'failed' ? uploadError : ''}
  />
</AppShell>

<style>
  .guided-shell {
    display: grid;
    gap: 0.9rem;
  }

  .hero,
  .panel {
    display: grid;
    gap: 0.95rem;
    padding: 1.2rem;
  }

  .hero {
    position: relative;
    grid-template-columns: minmax(0, 1fr);
    align-items: center;
    gap: 0.5rem;
    padding: 0.95rem 1rem;
    min-height: 6.25rem;
    border-radius: 12px;
    border: 1px solid rgba(96, 119, 214, 0.5);
    background:
      linear-gradient(135deg, rgba(255, 255, 255, 0.025), rgba(255, 255, 255, 0)),
      radial-gradient(circle at top left, rgba(72, 112, 255, 0.16), transparent 28%),
      radial-gradient(circle at 88% 18%, rgba(145, 92, 255, 0.14), transparent 22%),
      linear-gradient(180deg, rgba(12, 20, 48, 0.96), rgba(11, 19, 43, 0.98)),
      var(--surface);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.05),
      0 18px 40px rgba(4, 10, 28, 0.22);
  }

  .hero-copy {
    display: grid;
    gap: 0.35rem;
  }

  .hero-copy h2 {
    margin: 0;
    font-size: clamp(1.8rem, 2.4vw, 2.2rem);
    letter-spacing: 0;
    line-height: 1;
  }

  .hero-copy :global(.eyebrow) {
    margin: 0;
    font-size: 0.72rem;
    letter-spacing: 0.18em;
  }

  .intake-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.9rem;
  }

  .source-inspection {
    gap: 0.75rem;
  }

  .source-summary,
  .source-slide-list,
  .media-list {
    display: grid;
    gap: 0.75rem;
  }

  .source-summary {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
  }

  .source-summary h3,
  .source-summary :global(.eyebrow) {
    margin: 0;
  }

  .source-summary span,
  .source-slide-list small,
  .media-list small,
  .source-inspection__message {
    color: var(--text-muted);
  }

  .source-inspection__message {
    margin: 0;
  }

  .source-inspection__body {
    display: grid;
    gap: 0.75rem;
  }

  .source-slide-list {
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }

  .source-slide-list article,
  .media-list a {
    min-width: 0;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.65rem;
    background: var(--surface-subtle);
  }

  .source-slide-list article,
  .media-list a {
    display: grid;
    gap: 0.25rem;
  }

  .media-list {
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }

  .media-list a {
    color: var(--text);
    text-decoration: none;
  }

  .stepper {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.55rem;
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .stepper li {
    display: grid;
    gap: 0.3rem;
    min-height: 5.1rem;
    padding: 0.7rem 0.75rem;
    border-radius: 16px;
    opacity: 0.42;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.015));
    transition:
      opacity 160ms ease,
      transform 160ms ease,
      border-color 160ms ease,
      box-shadow 160ms ease,
      background 160ms ease;
  }

  .step-active {
    opacity: 1;
    border-color: rgba(96, 178, 255, 0.42);
    background: linear-gradient(180deg, rgba(96, 178, 255, 0.12), rgba(96, 178, 255, 0.05));
    transform: translateY(-1px);
  }

  .step-complete {
    opacity: 1;
    border-color: rgba(118, 238, 185, 0.4);
    background: linear-gradient(180deg, rgba(118, 238, 185, 0.1), rgba(118, 238, 185, 0.04));
    box-shadow: 0 0 0 1px rgba(118, 238, 185, 0.06), 0 0 18px rgba(118, 238, 185, 0.05);
  }

  .step-index {
    width: 1.75rem;
    height: 1.75rem;
    border-radius: 999px;
    display: grid;
    place-items: center;
    background: rgba(255, 255, 255, 0.08);
    font-size: 0.82rem;
    font-weight: 700;
  }

  .step-active .step-index {
    background: linear-gradient(135deg, rgba(74, 118, 255, 0.92), rgba(145, 92, 255, 0.9));
  }

  .step-complete .step-index {
    background: linear-gradient(135deg, rgba(86, 187, 255, 0.95), rgba(107, 233, 161, 0.95));
    color: #04111f;
  }

  .step-label,
  .muted {
    color: var(--muted);
  }

  .step-label {
    font-size: 0.82rem;
    line-height: 1.15;
    max-width: 5.5rem;
  }

  @media (max-width: 1100px) {
    .hero,
    .intake-grid {
      grid-template-columns: 1fr;
    }

    .stepper {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 720px) {
    .guided-shell {
      gap: 0.8rem;
      padding-bottom: 0.65rem;
    }

    .hero,
    .panel {
      padding: 1rem;
    }

    .stepper {
      grid-template-columns: 1fr;
    }
  }
</style>
