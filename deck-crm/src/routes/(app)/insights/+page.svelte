<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import EmptyState from '$components/EmptyState.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
</script>

<AppShell
  title="Insights"
  subtitle="Insights appear after AI analysis has produced findings, adaptation suggestions, and review pressure."
  activeNav="insights"
  deckLabel={data.workspace.workspace.name}
>
  <EmptyState
    eyebrow="Insights"
    title={data.workspace.deckCount === 0 ? 'No insights yet' : 'Insights live inside processed decks'}
    message={data.workspace.deckCount === 0
      ? 'There is nothing to analyse until the first PDF becomes structured slides, classified blocks, and findings.'
      : 'Open a live deck to review diligence findings and audience adaptation recommendations.'}
    primaryHref={data.workspace.deckCount === 0 ? '/welcome' : '/dashboard'}
    primaryLabel={data.workspace.deckCount === 0 ? 'Upload first deck' : 'Open dashboard'}
    secondaryHref="/decks"
    secondaryLabel="Open deck library"
  />
</AppShell>
