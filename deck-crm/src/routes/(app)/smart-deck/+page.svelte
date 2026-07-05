<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import LockedFeatureCard from '$components/LockedFeatureCard.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const activeDeckId = $derived(data.workspace.activeDeckId ?? data.decks[0]?.id ?? null);
</script>

<AppShell
  title="Smart Deck"
  subtitle="Open the active Smart Deck workspace or choose a deck to continue."
  activeNav="smart-deck-root"
  deckLabel={data.workspace.workspace.name}
>
  {#if data.workspace.deckCount === 0 || !activeDeckId}
    <LockedFeatureCard
      title="Smart Deck unlocks after the first upload"
      message="Upload a PDF or PowerPoint deck first so Deck AIStack can create a structured Smart Deck workspace."
    />
  {:else}
    <section class="panel choose-deck">
      <div class="eyebrow">Smart Deck workspace</div>
      <h2>Open your active Smart Deck</h2>
      <p class="muted">Use Smart Deck to review the generated workspace, slide structure, design versions, and deck-level generation controls.</p>

      <div class="choose-deck__actions">
        <a class="button" href={`/decks/${activeDeckId}/smart-deck`}>Open active Smart Deck</a>
        <a class="button secondary" href="/decks">Choose another deck</a>
      </div>

      <div class="deck-list" aria-label="Recent Smart Decks">
        {#each data.decks.slice(0, 4) as deck}
          <a href={`/decks/${deck.id}/smart-deck`} class:active={deck.id === activeDeckId}>
            <span>{deck.title}</span>
            <small>{deck.status}</small>
          </a>
        {/each}
      </div>
    </section>
  {/if}
</AppShell>

<style>
  .choose-deck {
    padding: 1.3rem;
    display: grid;
    gap: 1rem;
  }

  h2 {
    margin: 0;
  }

  .choose-deck__actions {
    display: flex;
    gap: 0.8rem;
    flex-wrap: wrap;
  }

  .deck-list {
    display: grid;
    gap: 0.65rem;
    margin-top: 0.25rem;
  }

  .deck-list a {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    padding: 0.85rem 0.95rem;
    border: 1px solid var(--line);
    border-radius: 12px;
    color: var(--ink);
    background: rgba(255, 255, 255, 0.02);
  }

  .deck-list a.active,
  .deck-list a:hover {
    border-color: var(--line-contrast);
    background: var(--surface-chip);
  }

  .deck-list small {
    color: var(--muted);
    text-transform: capitalize;
  }
</style>
