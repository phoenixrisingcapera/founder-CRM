<script lang="ts">
  import TopBar from '$components/TopBar.svelte';
  import type { Snippet } from 'svelte';

  interface Props {
    title: string;
    subtitle?: string;
    status?: string;
    deckLabel?: string;
    actions?: Snippet;
  }

  let { title, subtitle = '', status = '', deckLabel = 'Deck AIStack Workspace', actions }: Props = $props();
</script>

<TopBar {title} {subtitle} {status} {deckLabel} {actions} />
