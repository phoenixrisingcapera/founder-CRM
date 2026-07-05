<script lang="ts">
  import AppShell from '$lib/layouts/AppShell.svelte';

  let { children }: { children: import('svelte').Snippet } = $props();
</script>

<svelte:head>
  <meta name="robots" content="noindex, nofollow" />
</svelte:head>

<AppShell>
  {@render children()}
</AppShell>
