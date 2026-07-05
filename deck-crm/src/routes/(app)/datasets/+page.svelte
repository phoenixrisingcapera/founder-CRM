<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import EmptyState from '$components/EmptyState.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
</script>

<AppShell
  title="Datasets"
  subtitle="Structured deck data sources appear here after Deck AIStack has parsed real slides and blocks."
  activeNav="datasets"
  deckLabel={data.workspace.workspace.name}
>
  <EmptyState
    eyebrow="Datasets"
    title={data.workspace.deckCount === 0 ? 'No datasets yet' : 'Datasets follow uploaded decks'}
    message={data.workspace.deckCount === 0
      ? 'Datasets are generated from uploaded decks after extraction, block classification, and source structuring.'
      : 'Open a processed deck to inspect structured slides, block-level content, and downstream datasets.'}
    primaryHref={data.workspace.deckCount === 0 ? '/welcome' : '/decks'}
    primaryLabel={data.workspace.deckCount === 0 ? 'Upload first deck' : 'Open deck library'}
    secondaryHref="/templates"
    secondaryLabel="Browse templates"
  />
</AppShell>
