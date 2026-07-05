<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import EmptyState from '$components/EmptyState.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
</script>

<AppShell
  title="Exports"
  subtitle="Exports are created after reviewable suggestions have been accepted or staged for output."
  activeNav="exports-root"
  deckLabel={data.workspace.workspace.name}
>
  <EmptyState
    eyebrow="Exports"
    title={data.workspace.exportCount === 0 ? 'No exports generated yet' : 'Exports are tied to deck workflows'}
    message={data.workspace.exportCount === 0
      ? 'This area will list generated deliverables after a deck has been processed through review and export.'
      : 'Open a deck export workspace to inspect generated files and version history.'}
    primaryHref={data.workspace.deckCount === 0 ? '/welcome' : '/decks'}
    primaryLabel={data.workspace.deckCount === 0 ? 'Upload first deck' : 'Open deck library'}
    secondaryHref="/templates"
    secondaryLabel="Browse templates"
  />
</AppShell>
