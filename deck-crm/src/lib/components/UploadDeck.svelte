<script lang="ts">
  import { goto } from '$app/navigation';
  import type { ApiErrorBannerModel } from '$lib/api/apiError';
  import type { DeckExtractionStatus, SmartDeckProcessingStatus } from '$lib/api/deckService/workflow.client';
  import {
    getDeckWorkflowStatus
  } from '$lib/api/deckService/workflow.client';
  import DeckLoaderOverlay from './DeckLoaderOverlay.svelte';
  import UploadDeckWidget from '$lib/components/deckService/upload/UploadDeckWidget.svelte';
  import {
    buildUploadDeckWidgetViewModel,
    type DeckUploadStatus
  } from '$lib/components/deckService/upload/upload-deck.types';
  import type { UploadedDeckListItem } from '$lib/components/deckService/upload/uploaded-decks-list.types';
  import type { SaveConfirmationBannerModel } from '$lib/contracts/types';

  type SmartDeckLoaderStep = {
    label: string;
    status: 'pending' | 'running' | 'complete' | 'failed';
  };

  type Props = {
    eyebrow?: string;
    accept: string;
    deckId?: string;
    deckFile: File | null;
    deckDragActive: boolean;
    deckUploadStatus: DeckUploadStatus;
    deckExtractionStatus: DeckExtractionStatus;
    uploadError: string;
    saveConfirmation?: SaveConfirmationBannerModel | null;
    canContinueAfterUpload: boolean;
    buttonLabel?: string;
    maxFileLabel?: string;
    workspaceDecks?: UploadedDeckListItem[];
    workspaceDecksLoading?: boolean;
    workspaceDecksError?: string | null;
    workspaceDecksErrorBanner?: ApiErrorBannerModel | null;
    onDeckSelection: (event: Event) => void | Promise<void>;
    onDeckDragEnter: (event: DragEvent) => void;
    onDeckDragLeave: (event: DragEvent) => void;
    onDeckDrop: (event: DragEvent) => void | Promise<void>;
    onSelectDeck?: (deck: UploadedDeckListItem) => void;
    onRetryDeck?: (deckId: string) => void | Promise<void>;
    onRemoveDeck?: (deckId: string) => void | Promise<void>;
    onContinue: () => void;
    formatFileSize: (size: number) => string;
  };

  const PROCESSING_POLL_ATTEMPTS = 24;
  const PROCESSING_POLL_INTERVAL_MS = 1500;

  const smartDeckLoaderPhases = [
    {
      key: 'starting',
      label: 'Checking Smart Deck readiness',
      title: 'Checking your Smart Deck readiness...',
      subtitle: 'We are polling backend Smart Deck readiness to see whether the workspace can open.',
      statusLabel: 'Checking',
      progress: 18
    },
    {
      key: 'reading',
      label: 'Reading your uploaded slides',
      title: 'Reading your uploaded slides...',
      subtitle: 'We are waiting for backend proof that the uploaded slides were read.',
      statusLabel: 'Reading',
      progress: 38
    },
    {
      key: 'previews',
      label: 'Creating slide previews',
      title: 'Creating slide previews...',
      subtitle: 'We are waiting for backend proof that slide previews exist.',
      statusLabel: 'Previewing',
      progress: 62
    },
    {
      key: 'workspace',
      label: 'Preparing your Smart Deck workspace',
      title: 'Preparing your Smart Deck workspace...',
      subtitle: 'The workspace opens when backend proof says it is prepared.',
      statusLabel: 'Preparing',
      progress: 82
    },
    {
      key: 'opening',
      label: 'Opening your Smart Deck',
      title: 'Opening your Smart Deck...',
      subtitle: 'Your deck is ready to open.',
      statusLabel: 'Opening',
      progress: 96
    }
  ] as const;

  let {
    eyebrow = '1. Upload your deck',
    accept,
    deckId = '',
    deckFile,
    deckDragActive,
    deckUploadStatus,
    deckExtractionStatus,
    uploadError,
    saveConfirmation = null,
    canContinueAfterUpload,
    buttonLabel = '✨ Continue to Smart Deck',
    maxFileLabel = 'PDF, PPT, PPTX • Max 200MB',
    workspaceDecks = [],
    workspaceDecksLoading = false,
    workspaceDecksError = null,
    workspaceDecksErrorBanner = null,
    onDeckSelection,
    onDeckDragEnter,
    onDeckDragLeave,
    onDeckDrop,
    onSelectDeck,
    onRetryDeck,
    onRemoveDeck,
    onContinue,
    formatFileSize
  }: Props = $props();

  let startingSmartDeck = $state(false);
  let smartDeckLoaderPhaseIndex = $state(0);
  let smartDeckLoaderError = $state('');
  let latestWorkflowStatus = $state<SmartDeckProcessingStatus | null>(null);

  const activeSmartDeckPhase = $derived(smartDeckLoaderPhases[smartDeckLoaderPhaseIndex] ?? smartDeckLoaderPhases[0]);
  const activeSmartDeckSubtitle = $derived(
    latestWorkflowStatus?.message ? `${activeSmartDeckPhase.subtitle} ${latestWorkflowStatus.message}` : activeSmartDeckPhase.subtitle
  );
  const readinessBlocked = $derived(
    Boolean(latestWorkflowStatus && !latestWorkflowStatus.canOpenSmartDeck)
  );
  const smartDeckLoaderSteps = $derived.by<SmartDeckLoaderStep[]>(() =>
    smartDeckLoaderPhases.map((phase, index): SmartDeckLoaderStep => ({
      label: phase.label,
      status:
        smartDeckLoaderError && index === smartDeckLoaderPhaseIndex
          ? 'failed'
          : index < smartDeckLoaderPhaseIndex
            ? 'complete'
            : index === smartDeckLoaderPhaseIndex
              ? 'running'
              : 'pending'
    }))
  );

  const viewModel = $derived(
    buildUploadDeckWidgetViewModel({
      deckFile,
      deckDragActive,
      deckUploadStatus,
      deckExtractionStatus,
      uploadError,
      saveConfirmation,
      canContinueAfterUpload: canContinueAfterUpload && !startingSmartDeck,
      buttonLabel: startingSmartDeck
        ? 'Starting Smart Deck...'
        : Boolean(latestWorkflowStatus?.canOpenSmartDeck)
          ? 'Open Smart Deck'
          : buttonLabel,
      maxFileLabel,
      formatFileSize
    })
  );

  function wait(milliseconds: number) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
  }

  function smartDeckLoaderPhaseIndexFor(status: SmartDeckProcessingStatus | null | undefined) {
    if (!status) return 0;
    if (status.canOpenSmartDeck) return 4;
    const stage = status.activeStage ?? '';
    if (stage.startsWith('source_ingestion') || stage.startsWith('source_extraction')) return 1;
    if (stage.startsWith('miniatures') || stage.startsWith('brand_extraction')) return 2;
    if (stage.startsWith('smart_deck_context') || stage.startsWith('db_publisher')) return 3;
    if (stage.startsWith('preview_render') || stage.startsWith('apply_version') || stage.startsWith('export')) return 4;
    return 0;
  }

  const smartDeckLoaderSubtitle = $derived(activeSmartDeckSubtitle);

  const stalledPhaseLabel = $derived(readinessPhaseLabel(latestWorkflowStatus));

  async function openSmartDeckWhenReady(targetDeckId: string) {
    smartDeckLoaderPhaseIndex = 4;
    await wait(500);
    await goto(`/decks/${targetDeckId}/smart-deck`);
  }

  $effect(() => {
    const targetDeckId = deckId;
    if (!targetDeckId || deckUploadStatus !== 'saved') {
      latestWorkflowStatus = null;
      return;
    }

    let cancelled = false;
    const refreshStatus = async () => {
      const status = await getDeckWorkflowStatus(targetDeckId).catch(() => null);
      if (cancelled) return;
      latestWorkflowStatus = status;
    };

    void refreshStatus();
    const interval = window.setInterval(() => {
      void refreshStatus();
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  });

  async function pollSmartDeckReadiness(targetDeckId: string) {
    for (let attempt = 0; attempt < PROCESSING_POLL_ATTEMPTS; attempt += 1) {
      const status = await getDeckWorkflowStatus(targetDeckId)
        .then((nextStatus) => {
          latestWorkflowStatus = nextStatus;
          return nextStatus;
        })
        .catch(() => null);

      smartDeckLoaderPhaseIndex = smartDeckLoaderPhaseIndexFor(status);

      if (Boolean(status?.canOpenSmartDeck)) {
        await openSmartDeckWhenReady(targetDeckId);
        return;
      }

      await wait(PROCESSING_POLL_INTERVAL_MS);
    }

    throw new Error('Smart Deck is still processing. The workspace will not open until the service marks it ready.');
  }

  async function continueToSmartDeck() {
    if (!deckId) {
      onContinue();
      return;
    }

    startingSmartDeck = true;
    smartDeckLoaderPhaseIndex = 0;
    smartDeckLoaderError = '';

    try {
      const currentStatus =
        latestWorkflowStatus ??
        (await getDeckWorkflowStatus(deckId)
          .then((nextStatus) => {
            latestWorkflowStatus = nextStatus;
            return nextStatus;
          })
          .catch(() => null));
      if (Boolean(currentStatus?.canOpenSmartDeck)) {
        await openSmartDeckWhenReady(deckId);
        return;
      }

      smartDeckLoaderPhaseIndex = smartDeckLoaderPhaseIndexFor(currentStatus) || 1;
      await wait(650);
      await pollSmartDeckReadiness(deckId);
    } catch (error) {
      smartDeckLoaderError = error instanceof Error ? error.message : 'Could not load Smart Deck readiness.';
      await wait(3500);
      startingSmartDeck = false;
    }
  }

  function readinessPhaseLabel(status: SmartDeckProcessingStatus | null | undefined): string | null {
    if (!status) return null;
    return status.activeStage || activeSmartDeckPhase.label;
  }
</script>

<UploadDeckWidget
  {eyebrow}
  {accept}
  {deckDragActive}
  {viewModel}
  uploadedDecks={deckId ? workspaceDecks.filter((deck) => deck.id !== deckId) : workspaceDecks}
  uploadedDecksLoading={workspaceDecksLoading}
  uploadedDecksError={workspaceDecksError}
  uploadedDecksErrorBanner={workspaceDecksErrorBanner}
  selectedDeckId={deckId || null}
  {onDeckSelection}
  {onDeckDragEnter}
  {onDeckDragLeave}
  {onDeckDrop}
  {onSelectDeck}
  {onRetryDeck}
  {onRemoveDeck}
  onPrimaryAction={continueToSmartDeck}
/>

{#if latestWorkflowStatus?.activeStage}
  <section class="smart-deck-backend-action" aria-live="polite">
    <strong>Backend readiness step</strong>
    <p>{readinessPhaseLabel(latestWorkflowStatus) ?? latestWorkflowStatus.activeStage}</p>
  </section>
{/if}

{#if readinessBlocked}
  <section class="smart-deck-stalled" aria-live="polite">
    <div>
      <strong>Smart Deck is not ready</strong>
      <p>
        {#if stalledPhaseLabel}
          Backend is at {stalledPhaseLabel.toLowerCase()}.
        {:else}
          Processing has not reached the final readiness stage yet.
        {/if}
        Progress: {latestWorkflowStatus?.message ?? 'queued'}.
      </p>
    </div>
    <a class="button secondary" href={deckId ? `/decks/${deckId}/processing` : '/decks'} data-sveltekit-preload-data="off">View processing</a>
  </section>
{/if}

<DeckLoaderOverlay
  open={startingSmartDeck}
  title={activeSmartDeckPhase.title}
  subtitle={smartDeckLoaderSubtitle}
  statusLabel={activeSmartDeckPhase.statusLabel}
  progress={activeSmartDeckPhase.progress}
  steps={smartDeckLoaderSteps}
  errorMessage={smartDeckLoaderError}
/>

<style>
  .smart-deck-backend-action,
  .smart-deck-stalled {
    display: grid;
    gap: 0.75rem;
    margin-top: 0.75rem;
    border: 1px solid var(--line-strong);
    border-radius: 12px;
    padding: 0.85rem;
    background: color-mix(in srgb, var(--surface-soft) 88%, transparent);
  }

  .smart-deck-backend-action strong,
  .smart-deck-backend-action p,
  .smart-deck-stalled strong,
  .smart-deck-stalled p {
    margin: 0;
  }

  .smart-deck-backend-action p,
  .smart-deck-stalled p {
    color: var(--muted);
    line-height: 1.5;
  }
</style>
