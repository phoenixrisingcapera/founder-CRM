<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import DeckWorkspace from '$components/DeckWorkspace.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
  const selectedSlideId = $derived(data.graph.slides[0]?.id ?? '');
</script>

<AppShell
  title="Workspace overview"
  subtitle={`${data.graph.deck.audience} • ${data.graph.deck.purpose}`}
  status={data.graph.deck.status}
  deckLabel={data.graph.deck.title}
  currentDeckId={data.graph.deck.id}
  latestBatches={data.latestBatches}
  activeNav="smart-deck"
>
  {#snippet actions()}
    <a class="button" href={`/decks/${data.graph.deck.id}/smart-edit`}>Smart Edit</a>
    <a class="button secondary" href={`/decks/${data.graph.deck.id}/due-diligence`}>Due Diligence</a>
    <a class="button secondary" href={`/decks/${data.graph.deck.id}/export`}>Export</a>
  {/snippet}

  <DeckWorkspace graph={data.graph} selectedSlideId={selectedSlideId} hrefBase={`/decks/${data.graph.deck.id}/smart-deck`} />
</AppShell>
