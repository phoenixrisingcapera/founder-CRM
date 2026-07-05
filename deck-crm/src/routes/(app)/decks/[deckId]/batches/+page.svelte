<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import PageHeader from '$components/PageHeader.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const latestBatch = $derived(data.batches[0] ?? null);
</script>

<AppShell
  title="Iterations"
  subtitle="AI adaptation iterations from this uploaded deck appear here. The sidebar previews the latest three persisted iterations."
  status={data.graph.deck.status}
  deckLabel={data.graph.deck.title}
  currentDeckId={data.graph.deck.id}
  latestBatches={data.latestBatches}
  activeNav="batches"
>
  <section class="section-stack">
    <PageHeader
      eyebrow="Generation history"
      title="Iteration history"
      subtitle="This page holds the complete adaptation history for whole-deck and selected-slide iteration runs."
      aside={`${data.batches.length} persisted versions`}
    />

    <section class="panel final-deck-cta">
      <div>
        <div class="eyebrow">Final deck handoff</div>
        <h2>Create the final deck from the latest generated version</h2>
        <p class="muted">
          This opens the compile workflow for the latest version before creating the final deck.
        </p>
      </div>
      {#if latestBatch}
        <a class="button" href={`/decks/${data.graph.deck.id}/batches/${latestBatch.id}/compile`}>Prepare Full Deck</a>
      {:else}
        <button class="button" type="button" disabled>Prepare Full Deck</button>
      {/if}
    </section>

    {#if data.batches.length > 0}
      <section class="batch-grid">
        {#each data.batches as batch}
          <a class="panel batch-card" href={`/decks/${data.graph.deck.id}/batches/${batch.id}`}>
            <div class="section-head">
              <strong>{batch.batchName ?? `Version ${batch.batchNumber}`}</strong>
              <span class="pill">{batch.status}</span>
            </div>
            <p class="muted">
              {batch.scopeType === 'whole_deck' ? 'Whole deck' : `${batch.selectedSlideCount} selected slides`}
            </p>
            <div class="batch-card__meta">
              <span>Version {batch.batchNumber}</span>
              <span>{new Date(batch.createdAt).toLocaleString()}</span>
            </div>
          </a>
        {/each}
      </section>
    {:else}
      <section class="panel empty-panel">
        <strong>No iterations available yet</strong>
        <p class="muted">
          Create a design version from Smart Deck and it will appear here as a reviewable, non-destructive iteration.
        </p>
      </section>
    {/if}
  </section>
</AppShell>

<style>
  .batch-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  }

  .batch-card {
    display: grid;
    gap: 0.75rem;
    padding: 1.15rem;
  }

  .batch-card__meta {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    flex-wrap: wrap;
    color: var(--muted);
    font-size: 0.84rem;
  }

  .empty-panel {
    padding: 1.2rem;
    display: grid;
    gap: 0.7rem;
  }

  .final-deck-cta {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    padding: 1.2rem;
    border-color: rgba(24, 200, 255, 0.34);
  }

  .final-deck-cta h2 {
    margin: 0.35rem 0 0;
  }

  @media (max-width: 760px) {
    .final-deck-cta {
      display: grid;
    }
  }
</style>
