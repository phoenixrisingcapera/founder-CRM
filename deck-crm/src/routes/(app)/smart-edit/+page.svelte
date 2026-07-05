<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import LockedFeatureCard from '$components/LockedFeatureCard.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
</script>

<AppShell
  title="Smart Edit"
  subtitle="Block-level edits stay reviewable. The feature opens after a deck has been uploaded and classified."
  activeNav="smart-edit-root"
  deckLabel={data.workspace.workspace.name}
>
  {#if data.workspace.deckCount === 0}
    <LockedFeatureCard
      title="Smart Edit unlocks after the first upload"
      message="The editor needs real deck blocks and classifications before it can suggest controlled rewrites."
    />
  {:else}
    <section class="panel choose-deck">
      <div class="eyebrow">Choose a deck</div>
      <h2>Open Smart Edit from a live workspace</h2>
      <p class="muted">Smart Edit operates inside a deck so slide blocks, classifications, and revision history stay connected.</p>
      <div class="choose-deck__actions">
        {#each data.decks.slice(0, 3) as deck}
          <a class="button secondary" href={`/decks/${deck.id}/smart-edit`}>{deck.title}</a>
        {/each}
      </div>
    </section>
  {/if}
</AppShell>

<style>
  .choose-deck {
    padding: 1.3rem;
    display: grid;
    gap: 0.9rem;
  }

  h2 {
    margin: 0;
  }

  .choose-deck__actions {
    display: flex;
    gap: 0.8rem;
    flex-wrap: wrap;
  }
</style>
