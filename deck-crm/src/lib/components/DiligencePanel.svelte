<script lang="ts">
  import FindingCard from '$components/FindingCard.svelte';
  import type { AnalysisFinding } from '$types/domain';

  interface Props {
    findings: AnalysisFinding[];
  }

  let { findings }: Props = $props();
</script>

<aside class="panel diligence-panel">
  <div class="header">
    <div class="eyebrow">Diligence Findings</div>
    <span>{findings.length}</span>
  </div>
  {#if findings.length}
    {#each findings as finding}
      <FindingCard {finding} />
    {/each}
  {:else}
    <p class="muted">No findings yet. Run analysis to populate diligence gaps.</p>
  {/if}
</aside>

<style>
  .diligence-panel {
    padding: 1rem;
    display: grid;
    gap: 0.8rem;
    align-content: start;
  }

  .header {
    display: flex;
    justify-content: space-between;
    color: var(--muted);
  }
</style>
