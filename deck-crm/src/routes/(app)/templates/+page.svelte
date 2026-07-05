<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import EmptyState from '$components/EmptyState.svelte';
  import SampleTemplatesRow from '$components/SampleTemplatesRow.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
</script>

<AppShell
  title="Templates"
  subtitle="Browse structured starting points without drifting into a generic slide-generator aesthetic."
  activeNav="templates"
  deckLabel={data.workspace.workspace.name}
>
  <section class="section-stack">
    {#if data.workspace.deckCount === 0}
      <EmptyState
        eyebrow="Template gallery"
        title="Templates are available before the first upload"
        message="Browse sample starting points now, then upload the real source deck when you want the full diligence workflow."
        primaryHref="/welcome"
        primaryLabel="Upload first deck"
        secondaryHref="/templates"
        secondaryLabel="Stay in templates"
      />
    {/if}

    <SampleTemplatesRow templates={data.workspace.firstTimeTemplates} />
  </section>
</AppShell>
