<script lang="ts">
  import { goto } from '$app/navigation';
  import AppShell from '$components/AppShell.svelte';
  import PageHeader from '$components/PageHeader.svelte';
  import CompiledDeckPage from '$lib/components/decks/CompiledDeckPage.svelte';
  import type { CompiledDeckModel } from '$lib/api/finalDeck';
  import type { PageData } from './$types';

  type FinalizeDeckRequest = {
    batchId: string;
    slideVersionId?: string | null;
  };

  type FinalizeDeckResponse = {
    deckId: string;
    finalDeckId: string;
    compiledDeckId?: string | null;
    latestBatchId: string;
    status: 'ready';
  };

  async function finalizeDeck(deckId: string, payload: FinalizeDeckRequest): Promise<FinalizeDeckResponse> {
    const response = await fetch(`/api/decks/${deckId}/finalize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }

    return (await response.json()) as FinalizeDeckResponse;
  }

  let { data }: { data: PageData } = $props();

  let compiledDeck = $state<CompiledDeckModel | null>(null);
  let isCompiling = $state(false);
  let compileError = $state<string | null>(null);

  const keptVersionCount = $derived(data.batch.candidateSlides.filter((candidate) => candidate.status === 'applied').length);
  const keptOriginalCount = $derived(
    data.batch.candidateSlides.filter((candidate) => candidate.status === 'kept_original').length
  );
  const reviewedCandidateCount = $derived(keptVersionCount + keptOriginalCount);
  const unreviewedCandidateCount = $derived(Math.max(data.batch.candidateSlides.length - reviewedCandidateCount, 0));

  $effect(() => {
    if (!compiledDeck && data.compiledDeck) {
      compiledDeck = data.compiledDeck;
    }
  });

  async function compileFullDeck() {
    isCompiling = true;
    compileError = null;

    try {
      const result = await finalizeDeck(data.graph.deck.id, {
        batchId: data.batch.id
      });
      const compiledDeckId = result.compiledDeckId ?? result.finalDeckId;
      if (!compiledDeckId) {
        throw new Error('Compiled deck was created but no compiled deck id was returned.');
      }
      await goto(`/decks/${data.graph.deck.id}/compiled/${compiledDeckId}`);
      return;
    } catch (error) {
      compileError = error instanceof Error ? error.message : 'Could not compile the final deck.';
    } finally {
      isCompiling = false;
    }
  }
</script>

<AppShell
  title="Prepare full deck"
  subtitle="Compile accepted slide versions and kept originals into the final deck."
  status={compiledDeck?.status ?? data.batch.status}
  deckLabel={data.graph.deck.title}
  currentDeckId={data.graph.deck.id}
  latestBatches={data.latestBatches}
  activeNav={`batch:${data.batch.id}`}
>
  {#snippet actions()}
    <a class="button secondary" href={`/decks/${data.graph.deck.id}/batches/${data.batch.id}`}>Review iteration</a>
    <a class="button secondary" href="/decks">Deck library</a>
  {/snippet}

  <section class="section-stack">
    <PageHeader
      eyebrow="Compile workflow"
      title={data.batch.batchName ?? `Iteration ${data.batch.batchNumber}`}
      subtitle="This page owns final deck preparation for this specific iteration."
      aside={`${reviewedCandidateCount}/${data.batch.candidateSlides.length} decisions`}
    />

    <section class="compile-grid">
      <article class="panel compile-card">
        <div>
          <div class="eyebrow">Input</div>
          <h2>Iteration decisions</h2>
        </div>
        <dl>
          <div><dt>Accepted versions</dt><dd>{keptVersionCount}</dd></div>
          <div><dt>Originals kept</dt><dd>{keptOriginalCount}</dd></div>
          <div><dt>Unreviewed originals</dt><dd>{unreviewedCandidateCount}</dd></div>
        </dl>
      </article>

      <article class="panel compile-card">
        <div>
          <div class="eyebrow">Output</div>
          <h2>{compiledDeck ? 'Compiled deck ready' : 'Ready to compile'}</h2>
          <p class="muted">
            {compiledDeck
              ? 'The final deck has been prepared and can be opened for review.'
              : 'Compile creates the final deck from explicit review decisions.'}
          </p>
        </div>
        {#if compileError}
          <p class="compile-error">{compileError}</p>
        {/if}
        <div class="compile-actions">
          <button class="button" type="button" onclick={compileFullDeck} disabled={isCompiling}>
            {isCompiling ? 'Compiling...' : compiledDeck ? 'Recompile Full Deck' : 'Compile Full Deck'}
          </button>
          {#if compiledDeck}
            <button class="button secondary" type="button" onclick={() => goto(`/decks/${compiledDeck?.deckId}/compiled/${compiledDeck?.compiledDeckId}`)}>
              Open final deck
            </button>
          {/if}
        </div>
      </article>
    </section>

    <CompiledDeckPage deckId={data.graph.deck.id} batchId={data.batch.id} {compiledDeck} />
  </section>
</AppShell>

<style>
  .compile-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }

  .compile-card {
    min-height: 220px;
    padding: 1.2rem;
    display: grid;
    align-content: space-between;
    gap: 1rem;
  }

  h2,
  p,
  dl {
    margin: 0;
  }

  dl {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
  }

  dt {
    color: var(--muted);
    font-size: 0.86rem;
  }

  dd {
    margin: 0.25rem 0 0;
    font-size: 1.6rem;
    font-weight: 800;
  }

  .compile-actions {
    display: flex;
    gap: 0.7rem;
    flex-wrap: wrap;
  }

  .compile-error {
    color: var(--danger);
  }

  @media (max-width: 840px) {
    .compile-grid,
    dl {
      grid-template-columns: 1fr;
    }
  }
</style>
