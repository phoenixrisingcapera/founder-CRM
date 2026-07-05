<script lang="ts">
  import Sidebar from '$components/Sidebar.svelte';
  import type { DesignBatchPreview } from '@deck-aistack-codes/shared';

  interface Props {
    active?: string;
    currentDeckId?: string | null;
    latestBatches?: DesignBatchPreview[];
  }

  let { active = '', currentDeckId = null, latestBatches = [] }: Props = $props();
</script>

<Sidebar {active} {currentDeckId} {latestBatches} />
