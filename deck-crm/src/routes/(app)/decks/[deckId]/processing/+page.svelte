<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { deckProductApiPath } from '$lib/contracts';
  import AppShell from '$components/AppShell.svelte';
  import {
    getDeckWorkflowStatus,
    getWorkflowActivePhaseLabel,
    isWorkflowStatusStalled,
    type SmartDeckProcessingStatus
  } from '$lib/api/deckService/workflow.client';
  import { isApiAuthError } from '$lib/api/apiError';
  import type { PageData } from './$types';
  import type { SmartDeckProcessingStatusWithDiagnostics } from '$lib/api/deckService/workflow.client';

  let { data }: { data: PageData } = $props();

  const NORMAL_POLL_DELAY_MS = 3000;
  const REVIEW_POLL_DELAY_MS = 15000;
  const STALE_POLL_THRESHOLD = 10;
  const MAX_POLL_ATTEMPTS = 24;
  const DEFAULT_AUTH_EXPIRED_MESSAGE = 'Your session expired. Sign in again to continue processing this deck.';

  let status = $state<SmartDeckProcessingStatusWithDiagnostics | null>(null);
  let errorMessage = $state('');
  let authExpired = $state(false);
  let authExpiredMessage = $state('');
  let pollCount = $state(0);
  let actionInFlight = $state(false);
  let scheduleNextPoll: ((delayMs?: number) => void) | null = null;

  function isAuthFailure(error: unknown): boolean {
    if (isApiAuthError(error)) return true;
    const message = error instanceof Error ? error.message : String(error ?? '');
    return /authentication|required|sign.?in|session.*expired|missing.*token|invalid.*token|revoked/i.test(message);
  }

  function markAuthExpired(error: unknown) {
    authExpired = true;
    authExpiredMessage = error instanceof Error ? error.message : 'Authentication required';
    errorMessage = DEFAULT_AUTH_EXPIRED_MESSAGE;
  }

  function shouldContinuePolling(nextStatus: SmartDeckProcessingStatus | null): boolean {
    if (authExpired) return false;
    if (!nextStatus) return true;
    if (nextStatus.canOpenSmartDeck) return false;
    if (nextStatus.status === 'failed' || nextStatus.deckExtractionStatus === 'failed') {
      return false;
    }
    return true;
  }

  function pollDelayFor(nextStatus: SmartDeckProcessingStatus | null): number {
    if (pollCount >= STALE_POLL_THRESHOLD) return REVIEW_POLL_DELAY_MS;
    return NORMAL_POLL_DELAY_MS;
  }

  function statusKey(nextStatus: SmartDeckProcessingStatus): string {
    return JSON.stringify({
      lifecycleStatus: nextStatus.status,
      nextAction: nextStatus.nextAction,
      sourceFileSaved: nextStatus.sourceFileSaved,
      sourceFileStatus: nextStatus.sourceFileStatus,
      deckExtractionStatus: nextStatus.deckExtractionStatus,
      message: nextStatus.message,
      errorMessage: nextStatus.errorMessage,
      canOpenSmartDeck: nextStatus.canOpenSmartDeck,
      activeStage: nextStatus.activeStage,
      stages: nextStatus.stages,
      failures: nextStatus.failures
    });
  }

  $effect(() => {
    if (status === null) {
      status = data.status as SmartDeckProcessingStatus;
    }
  });

  async function readProcessingPayload(): Promise<SmartDeckProcessingStatus> {
    return getDeckWorkflowStatus(data.deckId);
  }

  async function handleRetryOrOpenSmartDeck() {
    if (actionInFlight || !data.deckId || authExpired) return;

    actionInFlight = true;
    errorMessage = '';

    try {
      if (status?.canOpenSmartDeck) {
        await goto(`/decks/${data.deckId}/smart-deck`, { invalidateAll: false, noScroll: true });
        return;
      }

      if (status?.status === 'failed' || status?.deckExtractionStatus === 'failed') {
        const response = await fetch(deckProductApiPath(`/decks/${data.deckId}/retry`), {
          method: 'POST'
        });
        const payload = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(typeof payload?.message === 'string' ? payload.message : 'Could not retry processing.');
        }
      }

      scheduleNextPoll?.(0);
    } catch (error) {
      if (isAuthFailure(error)) {
        markAuthExpired(error);
        return;
      }
      errorMessage = error instanceof Error ? error.message : 'Could not refresh Smart Deck processing.';
    } finally {
      actionInFlight = false;
    }
  }

  onMount(() => {
    let cancelled = false;
    let inFlight = false;
    let navigating = false;
    let timeout: number | null = null;
    let lastStatusKey = status ? statusKey(status) : '';

    const clearScheduledPoll = () => {
      if (timeout !== null) {
        window.clearTimeout(timeout);
        timeout = null;
      }
    };

    const runPoll = async () => {
      if (cancelled || inFlight || navigating || actionInFlight || !shouldContinuePolling(status)) return;
      inFlight = true;

      try {
        const nextStatus = await readProcessingPayload();
        if (cancelled) return;

        const nextKey = statusKey(nextStatus);
        if (nextKey !== lastStatusKey) {
          status = nextStatus;
          lastStatusKey = nextKey;
        }
        pollCount += 1;
        errorMessage = '';

        if (nextStatus.canOpenSmartDeck) {
          navigating = true;
          clearScheduledPoll();
          await goto(`/decks/${data.deckId}/smart-deck`, { invalidateAll: false, noScroll: true });
          return;
        }

        if (pollCount >= MAX_POLL_ATTEMPTS) {
          clearScheduledPoll();
          errorMessage = nextStatus?.message || 'Processing status has stalled. Refresh the page or continue when you open Smart Deck from the Processing page.';
          return;
        }
      } catch (error) {
        if (!cancelled) {
          if (error instanceof Error && error.name === 'DeckProcessingAuthExpiredError') {
            authExpired = true;
            authExpiredMessage = error.message || DEFAULT_AUTH_EXPIRED_MESSAGE;
            errorMessage = authExpiredMessage;
            clearScheduledPoll();
            return;
          }
          if (isAuthFailure(error)) {
            clearScheduledPoll();
            markAuthExpired(error);
          } else {
            errorMessage = error instanceof Error ? error.message : 'Could not refresh processing status.';
          }
        }
      } finally {
        inFlight = false;
        if (!cancelled && !navigating && shouldContinuePolling(status)) {
          scheduleNextPoll?.(pollDelayFor(status));
        }
      }
    };

    scheduleNextPoll = (delayMs = 0) => {
      if (cancelled || authExpired) return;
      clearScheduledPoll();
      timeout = window.setTimeout(() => {
        void runPoll();
      }, delayMs);
    };

    if (shouldContinuePolling(status)) {
      scheduleNextPoll(900);
    }

    return () => {
      cancelled = true;
      scheduleNextPoll = null;
      clearScheduledPoll();
    };
  });

  const isReady = $derived.by(() => Boolean(status?.canOpenSmartDeck));
  const hasFailure = $derived.by(() =>
    Boolean(status?.status === 'failed' || status?.deckExtractionStatus === 'failed')
  );
  const processingStalled = $derived.by(() => Boolean(isWorkflowStatusStalled(status) && !isReady && !hasFailure));
  const stalledPhaseLabel = $derived.by(() => getWorkflowActivePhaseLabel(status));
  const activeStageLabel = $derived.by(() => status?.stages?.find((phase) => phase.key === status?.activeStage)?.label ?? stalledPhaseLabel);
  const backendTroubleshootingUrl = $derived.by(() => `/admin/deployment-readiness?deckId=${encodeURIComponent(data.deckId)}`);
  const headline = $derived.by(() => {
    if (authExpired) return 'Sign in again to continue processing';
    if (isReady) return 'Smart Deck is ready';
    if (processingStalled) return 'Processing has stalled';
    if (hasFailure) return 'Processing failed';
    if (status?.status === 'processing') return 'Processing your deck';
    return 'Waiting for the Smart Deck worker';
  });
  const description = $derived.by(() => {
    if (authExpired) return authExpiredMessage || 'Your session expired. Sign in again to continue processing this deck.';
    if (isReady) return status?.message || 'The backend says the Smart Deck workspace can now open.';
    if (processingStalled) {
      const phase = stalledPhaseLabel ?? 'the current phase';
      return `The backend has stayed on ${phase.toLowerCase()} for a while. Retry the workflow or inspect the worker logs if it does not change soon.`;
    }
    if ((status?.errorMessage ?? '').includes('Converted PDF storage path is invalid')) {
      return 'The source file is saved, but the worker could not create the converted PDF cache path. Deploy the backend storage-path fix, then retry processing.';
    }
    if (hasFailure) {
      if (status?.backendStatus && status.backendStatus >= 500) {
        return `${status.backendMessage || 'The backend returned an error while loading workflow state.'} Check the deployment readiness page to verify the API and worker split.`;
      }
      return status?.errorMessage || status?.message || 'The worker could not complete this deck automatically. Retry processing or review the saved source file.';
    }
    return status?.message || 'The source file is saved. The backend worker pipeline is preparing the source-backed Smart Deck workspace.';
  });
</script>

<AppShell
  title="Smart Deck Processing"
  subtitle="Canonical backend state"
  activeNav="upload"
  showTopBarSearch={false}
  compactSidebar={true}
>
  <section class="panel processing-state" aria-live="polite" data-sveltekit-preload-data="off">
  <div class="processing-heading">
      <div>
        <div class="eyebrow">Canonical processing state</div>
        <h2>{headline}</h2>
        <p class="muted">{description}</p>
      </div>
      <div class="processing-pill" class:ready={isReady} class:failed={hasFailure || authExpired}>{authExpired ? 'auth_expired' : status?.status ?? 'processing'}</div>
    </div>

    {#if authExpired}
      <article class="auth-expired-panel">
        <strong>Your session expired. Sign in again to continue processing this deck.</strong>
        {#if authExpiredMessage}
          <p>{authExpiredMessage}</p>
        {/if}
        <a class="button" href={`/auth/sign-in?next=${encodeURIComponent(`/decks/${data.deckId}/processing`)}`} data-sveltekit-preload-data="off">Sign in again</a>
        <a class="button secondary" href="/decks/new?firstBatch=slide_miniatures" data-sveltekit-preload-data="off">Back to upload</a>
      </article>
    {:else}
      <div class="phase-list" aria-label="Processing phases">
        {#each (status?.phases ?? []) as phase}
          <article class="phase" class:active={phase.status === 'active'} class:completed={phase.status === 'completed'} class:failed={phase.status === 'failed'}>
            <span class="phase-marker" aria-hidden="true">
              {phase.status === 'completed' ? 'done' : phase.status === 'failed' ? '!' : phase.status === 'active' ? '...' : 'o'}
            </span>
            <div>
              <strong>{phase.label}</strong>
              {#if phase.description}
                <p>{phase.description}</p>
              {/if}
              {#if typeof phase.count === 'number'}
                <small>{phase.count} item{phase.count === 1 ? '' : 's'}</small>
              {/if}
            </div>
          </article>
        {/each}
      </div>

      <div class="processing-grid">
        <article>
          <span>Next action</span>
          <strong>{status?.nextAction ?? 'wait_for_processing'}</strong>
        </article>
        <article>
          <span>Status</span>
          <strong>{status?.status ?? 'queued'}</strong>
        </article>
        <article>
          <span>Source file</span>
          <strong>{status?.sourceFileSaved ? 'saved' : 'not confirmed'}</strong>
        </article>
        <article>
          <span>Current stage</span>
          <strong>{status?.processingStageLabel ?? activeStageLabel ?? status?.processingStage ?? 'processing'}</strong>
        </article>
        <article>
          <span>Checks</span>
          <strong>{pollCount}</strong>
        </article>
      </div>

      {#if status?.missingArtifacts?.length}
        <div class="processing-note warning">
          <strong>Missing artifacts</strong>
          <p>{status.missingArtifacts.join(', ')}</p>
        </div>
      {/if}

      {#if status?.failures?.length}
        <div class="processing-note warning">
          <strong>Failure tickets</strong>
          <p>{status.failures.length} failure ticket(s) reported by the backend.</p>
        </div>
      {/if}

      {#if status?.backendStatus}
        <div class="processing-note warning">
          <strong>Backend response</strong>
          <p>
            Workflow-state returned HTTP {status.backendStatus}{status.backendStatusText ? ` ${status.backendStatusText}` : ''}.
            {status.backendMessage ?? 'Inspect deployment readiness and backend logs for the exact failure.'}
          </p>
          <a class="button secondary" href={backendTroubleshootingUrl} data-sveltekit-preload-data="off">
            Open deployment readiness
          </a>
        </div>
      {/if}

      <div class="actions" data-sveltekit-preload-data="off">
        {#if isReady}
          <a class="button" href={`/decks/${data.deckId}/smart-deck`} data-sveltekit-preload-data="off">Open Smart Deck</a>
        {:else if processingStalled}
          <button type="button" class="button" onclick={handleRetryOrOpenSmartDeck} disabled={actionInFlight}>
            {actionInFlight ? 'Retrying...' : 'Retry processing'}
          </button>
          <a class="button secondary" href="/decks/new?firstBatch=slide_miniatures" data-sveltekit-preload-data="off">Back to upload</a>
        {:else if hasFailure}
          <button type="button" class="button" onclick={handleRetryOrOpenSmartDeck} disabled={actionInFlight}>
            {actionInFlight ? 'Retrying...' : 'Retry processing'}
          </button>
          <a class="button secondary" href="/decks/new">Upload another deck</a>
        {:else}
          <button class="button secondary" type="button" onclick={() => scheduleNextPoll?.(0)}>Refresh status</button>
        {/if}
      </div>
    {/if}

    {#if errorMessage}
      <p class="error-copy">{errorMessage}</p>
    {/if}
  </section>
</AppShell>

<style>
  .processing-state {
    display: grid;
    gap: 1rem;
    max-width: 980px;
    padding: 1.25rem;
  }

  h2,
  p {
    margin: 0;
  }

  .processing-heading {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }

  .processing-pill {
    border: 1px solid var(--border, var(--line));
    border-radius: 999px;
    padding: 0.35rem 0.75rem;
    color: var(--text-muted, var(--muted));
    background: var(--surface-subtle, var(--surface-soft));
    white-space: nowrap;
  }

  .processing-pill.ready {
    color: var(--success, #5ee6a8);
  }

  .processing-pill.failed {
    color: var(--danger, #ff6b6b);
  }

  .auth-expired-panel {
    display: grid;
    gap: 0.75rem;
    border: 1px solid var(--danger, #ff6b6b);
    border-radius: 12px;
    padding: 1rem;
    background: color-mix(in srgb, var(--danger, #ff6b6b) 9%, transparent);
  }

  .auth-expired-panel p {
    color: var(--text-muted, var(--muted));
  }

  .phase-list {
    display: grid;
    gap: 0.65rem;
  }

  .phase {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.75rem;
    border: 1px solid var(--border, var(--line));
    border-radius: 12px;
    padding: 0.8rem;
    background: var(--surface-subtle, var(--surface-soft));
  }

  .phase.active {
    border-color: var(--accent, #8b5cf6);
  }

  .phase.completed {
    opacity: 0.88;
  }

  .phase.failed {
    border-color: var(--danger, #ff6b6b);
  }

  .phase-marker {
    display: grid;
    place-items: center;
    min-width: 1.6rem;
    height: 1.6rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.06);
    font-size: 0.72rem;
  }

  .phase p {
    margin-top: 0.25rem;
    color: var(--text-muted, var(--muted));
  }

  .phase small {
    display: inline-block;
    margin-top: 0.35rem;
    color: var(--text-muted, var(--muted));
  }

  .processing-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.75rem;
  }

  .processing-grid article {
    display: grid;
    gap: 0.25rem;
    border: 1px solid var(--border, var(--line));
    border-radius: 10px;
    padding: 0.75rem;
    background: var(--surface-subtle, var(--surface-soft));
  }

  .processing-grid span {
    color: var(--text-muted, var(--muted));
    font-size: 0.8rem;
  }

  .error-copy {
    color: var(--danger, #ff6b6b);
  }

  .processing-note {
    display: grid;
    gap: 0.25rem;
    border: 1px solid var(--border, var(--line));
    border-radius: 12px;
    padding: 0.85rem 1rem;
    background: var(--surface-subtle, var(--surface-soft));
  }

  .processing-note.warning {
    border-color: color-mix(in srgb, var(--warning, #f59e0b) 55%, var(--border, var(--line)));
  }

  .processing-note p {
    color: var(--text-muted, var(--muted));
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  button:disabled {
    opacity: 0.65;
    cursor: wait;
  }
</style>
