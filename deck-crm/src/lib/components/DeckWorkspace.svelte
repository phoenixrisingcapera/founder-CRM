<script lang="ts">
  import DiligencePanel from '$components/DiligencePanel.svelte';
  import SlideList from '$components/SlideList.svelte';
  import SlideViewer from '$components/SlideViewer.svelte';
  import SuggestionCard from '$components/SuggestionCard.svelte';
  import type { DeckGraph } from '$types/domain';

  interface Props {
    graph: DeckGraph;
    selectedSlideId: string;
    hrefBase: string;
  }

  let { graph, selectedSlideId, hrefBase }: Props = $props();
  const selectedSlide = $derived(graph.slides.find((slide) => slide.id === selectedSlideId) ?? graph.slides[0]);
  const slideSuggestions = $derived(graph.suggestions.filter((item) => item.slideId === selectedSlide?.id));
</script>

<div class="grid-3">
  <SlideList slides={graph.slides} selectedSlideId={selectedSlide?.id} {hrefBase} />
  {#if selectedSlide}
    <SlideViewer slide={selectedSlide} />
  {/if}
  <div class="workspace-right">
    <DiligencePanel findings={graph.findings.filter((finding) => finding.slideId === selectedSlide?.id)} />
    <section class="panel suggestion-panel">
      <div class="header">
        <div class="eyebrow">Audience Recommendations</div>
        <span>{slideSuggestions.length}</span>
      </div>
      {#each slideSuggestions as suggestion}
        <SuggestionCard {suggestion} />
      {/each}
    </section>
  </div>
</div>

<style>
  .workspace-right {
    display: grid;
    gap: 1rem;
    align-content: start;
  }

  .suggestion-panel {
    padding: 1rem;
    display: grid;
    gap: 0.8rem;
  }

  .header {
    display: flex;
    justify-content: space-between;
    color: var(--muted);
  }
</style>
