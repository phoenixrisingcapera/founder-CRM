<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import PageHeader from '$components/PageHeader.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
  const compiledDeck = $derived(data.compiledDeck);

  function slideSourceLabel(choice: string) {
    return choice === 'generated_version' ? 'Accepted version' : 'Original slide';
  }

  function slideBody(slide: PageData['compiledDeck']['slides'][number]) {
    const manifest = slide.manifest ?? {};
    const content = (manifest.contentJson ?? {}) as Record<string, unknown>;
    return String(content.summary ?? content.headline ?? content.rawText ?? 'No slide body available.');
  }
</script>

<AppShell
  title={compiledDeck.title}
  subtitle={`${compiledDeck.slideCount} compiled slides · ${compiledDeck.status}`}
  status={compiledDeck.status}
  deckLabel={compiledDeck.title}
  currentDeckId={compiledDeck.deckId}
  activeNav="decks"
>
  {#snippet actions()}
    <a class="button" href={`/decks/${compiledDeck.deckId}/export`}>Export deck</a>
    <a class="button secondary" href={`/decks/${compiledDeck.deckId}/batches/${compiledDeck.batchId}`}>Review iteration</a>
    <a class="button secondary" href="/decks">Deck library</a>
  {/snippet}

  <section class="section-stack">
    <PageHeader
      eyebrow="Compiled deck"
      title={compiledDeck.title}
      subtitle="Rendered from accepted generated versions, explicit original choices, and untouched original slides."
      aside={new Date(compiledDeck.finalizedAt).toLocaleString()}
    />

    <section class="compiled-grid">
      {#each compiledDeck.slides as slide}
        <article class="panel compiled-slide">
          <div class="compiled-slide__meta">
            <span>Slide {String(slide.slideIndex).padStart(2, '0')}</span>
            <span>{slideSourceLabel(slide.choice)}</span>
          </div>
          <h2>{slide.title}</h2>
          <p>{slideBody(slide)}</p>
        </article>
      {/each}
    </section>
  </section>
</AppShell>

<style>
  .compiled-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
  }

  .compiled-slide {
    min-height: 220px;
    padding: 1.1rem;
    display: grid;
    align-content: start;
    gap: 0.85rem;
  }

  .compiled-slide__meta {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .compiled-slide__meta span {
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 0.35rem 0.55rem;
    color: var(--ink-soft);
    font-size: 0.82rem;
  }

  .compiled-slide h2 {
    margin: 0;
    font-size: 1.1rem;
  }

  .compiled-slide p {
    margin: 0;
    color: var(--muted);
  }
</style>
