<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import FirstTimeDashboard from '$components/FirstTimeDashboard.svelte';
  import ReturningUserDashboard from '$components/ReturningUserDashboard.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
</script>

<AppShell
  title="Dashboard"
  subtitle="Resume your deck work, review new iterations, and prepare investor-ready exports."
  activeNav="dashboard"
  deckLabel="Deck AIStack Workspace"
  currentDeckId={data.dashboard.latestDeck?.id ?? data.workspace.activeDeckId}
  latestBatches={data.latestBatches}
>
  {#snippet actions()}
    <a class="button" href={data.dashboard.stats.uploadedDecks === 0 ? '/welcome' : '/decks/new'}>
      {data.dashboard.stats.uploadedDecks === 0 ? 'Upload first deck' : 'New deck'}
    </a>
  {/snippet}

  {#if data.dashboard.stats.uploadedDecks === 0}
    <FirstTimeDashboard workspace={data.workspace} aiProviderSummary={data.aiProviderSummary} />
  {:else}
    <ReturningUserDashboard dashboard={data.dashboard} />
  {/if}
</AppShell>
