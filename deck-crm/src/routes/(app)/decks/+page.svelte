<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import DeckLibraryPage from '$lib/components/decks/DeckLibraryPage.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
</script>

<AppShell
  title="Deck library"
  subtitle="Manage uploaded decks, recent decks, and final deck handoffs."
  activeNav="decks"
  deckLabel="All decks"
>
  {#snippet actions()}
    <a class="button" href={data.workspace.deckCount === 0 ? '/welcome' : '/decks/new'}>
      {data.workspace.deckCount === 0 ? 'Upload first deck' : 'New deck'}
    </a>
  {/snippet}

  <DeckLibraryPage
    workspace={data.workspace}
    decks={data.decks}
    latestGeneratedDeck={data.latestGeneratedDeck}
  />
</AppShell>
