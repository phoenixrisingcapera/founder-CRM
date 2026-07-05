<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import DiligencePanel from '$components/DiligencePanel.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
</script>

<AppShell
  title={`${data.graph.deck.title} diligence`}
  subtitle="Deck-wide findings and evidence gaps."
  currentDeckId={data.graph.deck.id}
  latestBatches={data.latestBatches}
  activeNav="diligence"
>
  <DiligencePanel findings={data.graph.findings} />
</AppShell>
