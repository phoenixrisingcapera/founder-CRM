<script lang="ts">
  import DashboardRightRail from '$components/dashboard/DashboardRightRail.svelte';
  import DashboardWelcomeHero from '$components/dashboard/DashboardWelcomeHero.svelte';
  import RecentSlidesPreview from '$components/dashboard/RecentSlidesPreview.svelte';
  import UploadedDecksPanel from '$components/dashboard/UploadedDecksPanel.svelte';
  import type { WorkspaceDashboardResponse } from '$lib/types/workspace-dashboard';

  interface Props {
    dashboard: WorkspaceDashboardResponse;
  }

  let { dashboard }: Props = $props();
</script>

<section class="returning-dashboard">
  <main class="dashboard-main">
    <DashboardWelcomeHero user={dashboard.user} stats={dashboard.stats} latestDeck={dashboard.latestDeck} />

    {#if dashboard.latestDeck}
      <RecentSlidesPreview deck={dashboard.latestDeck} slides={dashboard.recentSlides} />
    {/if}

    <UploadedDecksPanel decks={dashboard.decks} />
  </main>

  <DashboardRightRail
    latestDeck={dashboard.latestDeck}
    stats={dashboard.stats}
    latestIterations={dashboard.latestIterations}
  />
</section>

<style>
  .returning-dashboard {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 360px;
    gap: 1rem;
    align-items: start;
  }

  .dashboard-main {
    display: grid;
    gap: 1rem;
    min-width: 0;
  }

  @media (max-width: 1180px) {
    .returning-dashboard {
      grid-template-columns: 1fr;
    }
  }
</style>
