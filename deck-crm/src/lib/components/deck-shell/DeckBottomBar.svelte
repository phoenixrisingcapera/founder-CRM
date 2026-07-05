<script lang="ts">
  import type { DesignBatchPreview } from '@deck-aistack-codes/shared';

  interface Props {
    selectedBlockCount: number;
    classificationCount: number;
    revisionCount: number;
    latestBatch?: DesignBatchPreview | null;
  }

  let { selectedBlockCount, classificationCount, revisionCount, latestBatch = null }: Props = $props();
</script>

<footer class="deck-bottom-bar panel">
  <span>Saved</span>
  <span>{selectedBlockCount} editable blocks on the selected slide</span>
  <span>{classificationCount} content tags available for this slide</span>
  <span>{revisionCount} reviewed revisions in this deck</span>
  <span>{latestBatch ? `Version ${latestBatch.batchNumber}` : 'Version 0'}</span>
</footer>

<style>
  .deck-bottom-bar {
    display: flex;
    gap: 0.9rem;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    padding: 0.9rem 1rem;
    color: var(--muted);
    font-size: 0.9rem;
  }
</style>
