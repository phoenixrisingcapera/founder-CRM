<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import ExportPanel from '$components/ExportPanel.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
</script>

<AppShell
  title="Export"
  subtitle="Select the output artifact and generate a review-ready export."
  status={data.graph.deck.status}
  deckLabel={data.graph.deck.title}
  currentDeckId={data.graph.deck.id}
  latestBatches={data.latestBatches}
  activeNav="exports"
>
  <ExportPanel deckId={data.graph.deck.id} exports={data.exports} />
</AppShell>
