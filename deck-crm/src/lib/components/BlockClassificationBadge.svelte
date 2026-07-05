<script lang="ts">
  interface Props {
    semanticTag: string;
    diligenceCategory: string;
  }

  let { semanticTag, diligenceCategory }: Props = $props();
</script>

<div class="badge-group">
  <span class="pill">{semanticTag}</span>
  <span class="pill">{diligenceCategory}</span>
</div>

<style>
  .badge-group {
    display: flex;
    gap: 0.45rem;
    flex-wrap: wrap;
  }
</style>
