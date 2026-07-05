<script lang="ts">
  import { goto } from '$app/navigation';
  import AppShell from '$components/AppShell.svelte';
  import PageHeader from '$components/PageHeader.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
  let batchOverride = $state<PageData['batch'] | null>(null);
  let isSavingCandidateId = $state<string | null>(null);
  let reviewError = $state<string | null>(null);
  let finalizeError = $state<string | null>(null);
  const batch = $derived(batchOverride ?? data.batch);
  const keptVersionCount = $derived(batch.candidateSlides.filter((candidate) => candidate.status === 'applied').length);
  const keptOriginalCount = $derived(
    batch.candidateSlides.filter((candidate) => candidate.status === 'kept_original').length
  );
  const reviewedCandidateCount = $derived(keptVersionCount + keptOriginalCount);
  const allCandidatesReviewed = $derived(
    batch.candidateSlides.length > 0 && reviewedCandidateCount === batch.candidateSlides.length
  );

  async function reviewCandidate(candidateId: string, decision: 'keep_version' | 'keep_original') {
    isSavingCandidateId = candidateId;
    reviewError = null;
    finalizeError = null;

    try {
      const currentCandidate = batch.candidateSlides.find((candidate) => candidate.id === candidateId);
      if (!currentCandidate?.sourceSlideId) {
        throw new Error('Generated candidate is missing a source slide link.');
      }

      const response = await fetch(`/api/decks/${data.graph.deck.id}/batches/${batch.id}/slide-decisions/${currentCandidate.sourceSlideId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          choice: decision === 'keep_version' ? 'generated_version' : 'original',
          generatedSlideVersionId: decision === 'keep_version' ? candidateId : null
        })
      });
      const payload = (await response.json().catch(() => null)) as { batch?: PageData['batch']; message?: string } | null;

      if (!response.ok) {
        throw new Error(typeof payload?.message === 'string' ? payload.message : 'Could not save the review decision.');
      }

      const reviewedStatus: PageData['batch']['candidateSlides'][number]['status'] =
        decision === 'keep_version' ? 'applied' : 'kept_original';
      const previousStatuses = new Map(batch.candidateSlides.map((candidate) => [candidate.id, candidate.status]));
      const nextBatch = payload?.batch ?? batch;
      const candidateSlides: PageData['batch']['candidateSlides'] = nextBatch.candidateSlides.map((candidate) => {
        if (candidate.id === candidateId) {
          return { ...candidate, status: reviewedStatus };
        }

        const previousStatus = previousStatuses.get(candidate.id);
        return previousStatus && previousStatus !== 'reviewable' ? { ...candidate, status: previousStatus } : candidate;
      });
      const isReviewed = candidateSlides.every((candidate) => candidate.status !== 'reviewable');

      batchOverride = {
        ...nextBatch,
        status: isReviewed ? 'reviewed' : nextBatch.status,
        candidateSlides
      };
    } catch (error) {
      reviewError = error instanceof Error ? error.message : 'Could not save the review decision.';
    } finally {
      isSavingCandidateId = null;
    }
  }

  function candidateStatusLabel(status: string) {
    if (status === 'applied') return 'Version kept';
    if (status === 'kept_original') return 'Original kept';
    return 'Ready for review';
  }

  function prepareFullDeck() {
    if (batch.status !== 'completed' && batch.status !== 'reviewed') {
      finalizeError = 'The iteration must finish generation before preparing the deck.';
      return;
    }

    finalizeError = null;
    void goto(`/decks/${data.graph.deck.id}/batches/${batch.id}/compile`);
  }
</script>

<AppShell
  title={`Iteration ${data.batch.batchNumber}`}
  subtitle="Each version stays reviewable and non-destructive. The uploaded deck is never overwritten by iteration creation."
  status={data.graph.deck.status}
  deckLabel={data.graph.deck.title}
  currentDeckId={data.graph.deck.id}
  latestBatches={data.latestBatches}
  activeNav={`batch:${data.batch.id}`}
>
  <section class="section-stack">
    <PageHeader
      eyebrow="Iteration detail"
      title={batch.batchName ?? `Iteration ${batch.batchNumber}`}
      subtitle={`${batch.scopeType === 'whole_deck' ? 'Whole deck' : `${batch.selectedSlideCount} slides`} • ${batch.status}`}
      aside={new Date(batch.createdAt).toLocaleString()}
    />

    <section class="panel detail-panel">
      <div><strong>Iteration number</strong><p>{batch.batchNumber}</p></div>
      <div><strong>Scope</strong><p>{batch.scopeType}</p></div>
      <div><strong>Selected slides</strong><p>{batch.selectedSlideCount}</p></div>
      <div><strong>Status</strong><p>{batch.status}</p></div>
      <div><strong>Audience</strong><p>{batch.audienceLabel ?? data.graph.deck.audience}</p></div>
      <div class="detail-panel__wide"><strong>Prompt</strong><p>{batch.prompt}</p></div>
      <div class="detail-panel__wide">
        <strong>Slide selection</strong>
        <div class="detail-panel__tag-row">
          {#each batch.selectedSlideIds as slideId}
            <span class="pill">{data.graph.slides.find((slide) => slide.id === slideId)?.title ?? slideId}</span>
          {/each}
        </div>
      </div>
      <div class="detail-panel__wide">
        <strong>Generated candidates</strong>
        {#if reviewError}
          <p class="detail-panel__error">{reviewError}</p>
        {/if}
        <div class="detail-panel__candidate-grid">
          {#each batch.candidateSlides as candidate}
            <article class="detail-panel__candidate">
              <div class="section-head">
                <strong>{candidate.title}</strong>
                <span class="pill">{candidateStatusLabel(candidate.status)}</span>
              </div>
              <p class="muted">Slide {String(candidate.slideIndex).padStart(2, '0')}</p>
              <p>{candidate.headline}</p>
              <p class="muted">{candidate.summary}</p>
              <div class="detail-panel__candidate-actions">
                <button
                  type="button"
                  class={candidate.status === 'applied' ? 'button selected' : 'button'}
                  onclick={() => reviewCandidate(candidate.id, 'keep_version')}
                  disabled={isSavingCandidateId === candidate.id}
                >
                  {isSavingCandidateId === candidate.id ? 'Saving...' : candidate.status === 'applied' ? 'Keep version ✓' : 'Keep version'}
                </button>
                <button
                  type="button"
                  class={candidate.status === 'kept_original' ? 'button secondary selected' : 'button secondary'}
                  onclick={() => reviewCandidate(candidate.id, 'keep_original')}
                  disabled={isSavingCandidateId === candidate.id}
                >
                  {candidate.status === 'kept_original' ? 'Keep original ✓' : 'Keep original'}
                </button>
              </div>
            </article>
          {/each}
        </div>
        <div class="detail-panel__prepare-card">
          <div>
            <strong>Prepare full deck</strong>
            <p>
{reviewedCandidateCount}/{batch.candidateSlides.length} explicit decisions · {keptVersionCount} versions kept ·
              {keptOriginalCount + (batch.candidateSlides.length - reviewedCandidateCount)} originals will be kept
            </p>
            {#if finalizeError}
              <p class="detail-panel__error">{finalizeError}</p>
            {/if}
          </div>
          <button type="button" class="button" onclick={prepareFullDeck} disabled={batch.status !== 'completed' && batch.status !== 'reviewed'}>
            Prepare Full Deck
          </button>
        </div>
      </div>
    </section>
  </section>
</AppShell>

<style>
  .detail-panel {
    padding: 1.2rem;
    display: grid;
    gap: 0.9rem;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .detail-panel p {
    margin: 0.3rem 0 0;
    color: var(--muted);
  }

  .detail-panel__wide {
    grid-column: 1 / -1;
  }

  .detail-panel__tag-row,
  .detail-panel__candidate-grid {
    display: grid;
    gap: 0.75rem;
  }

  .detail-panel__tag-row {
    grid-template-columns: repeat(auto-fit, minmax(160px, max-content));
  }

  .detail-panel__candidate-grid {
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  }

  .detail-panel__candidate {
    border: 1px solid var(--line);
    border-radius: 20px;
    background: var(--surface-soft);
    padding: 1rem;
    display: grid;
    gap: 0.8rem;
  }

  .detail-panel__candidate p:first-of-type {
    color: var(--ink);
  }

  .detail-panel__candidate-actions {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
  }

  .button.selected {
    box-shadow: 0 0 0 2px rgba(24, 200, 255, 0.32);
  }

  .detail-panel__prepare-card {
    margin-top: 1rem;
    border: 1px solid var(--line);
    border-radius: 20px;
    background: var(--surface);
    padding: 1rem;
    display: flex;
    gap: 1rem;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .detail-panel__error {
    color: var(--danger);
  }

  @media (max-width: 760px) {
    .detail-panel {
      grid-template-columns: 1fr;
    }

    .detail-panel__prepare-card .button {
      width: 100%;
    }
  }
</style>
