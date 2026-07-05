<script lang="ts">
  import type { DeckShellProperties, DeckShellToolId } from '@deck-aistack-codes/shared';
  import DeckSlideRail from '$components/deck-shell/DeckSlideRail.svelte';
  import type { BlockClassification, DeckGraph } from '$types/domain';

  interface Props {
    graph: DeckGraph;
    properties?: DeckShellProperties;
    activeTool: DeckShellToolId;
    workspaceHrefBase?: string;
    selectedSlideId?: string;
    selectedSlideIds: string[];
    recommendationCounts: Record<string, number>;
    findingSeverities: Record<string, string | undefined>;
    isAddingSlide?: boolean;
    allowAddSlide?: boolean;
    onToggleSlideSelection?: (slideId: string) => void;
    onSelectSlide?: (slideId: string) => void;
    onSelectAll?: () => void;
    onClearSelection?: () => void;
    onAddSlide?: () => void;
  }

  let {
    graph,
    properties,
    activeTool,
    workspaceHrefBase = `/decks/${graph.deck.id}/smart-deck`,
    selectedSlideId,
    selectedSlideIds,
    recommendationCounts,
    findingSeverities,
    isAddingSlide = false,
    allowAddSlide = true,
    onToggleSlideSelection,
    onSelectSlide,
    onSelectAll,
    onClearSelection,
    onAddSlide
  }: Props = $props();

  const selectedSlide = $derived(graph.slides.find((slide) => slide.id === selectedSlideId) ?? graph.slides[0]);
  const selectedBlocks = $derived(graph.blocks.filter((block) => block.slideId === selectedSlide?.id));
  const metricBlocks = $derived(selectedBlocks.filter((block) => block.blockType === 'metric'));
  const textBlocks = $derived(
    selectedBlocks.filter((block) => ['headline', 'title', 'body', 'bullet', 'quote'].includes(block.blockType))
  );
  const selectedFindings = $derived(graph.findings.filter((finding) => finding.slideId === selectedSlide?.id));
  const selectedSuggestions = $derived(graph.suggestions.filter((suggestion) => suggestion.slideId === selectedSlide?.id));
  const roleCounts = $derived(
    graph.slides.reduce<Record<string, number>>((counts, slide) => {
      counts[slide.role] = (counts[slide.role] ?? 0) + 1;
      return counts;
    }, {})
  );
  const topRoles = $derived(Object.entries(roleCounts).sort((left, right) => right[1] - left[1]).slice(0, 6));
  const selectedClassifications = $derived(
    graph.classifications.filter((classification: BlockClassification) =>
      selectedBlocks.some((block) => block.id === classification.blockId)
    )
  );
</script>

{#if activeTool === 'slides'}
  <DeckSlideRail
    deckId={graph.deck.id}
    slides={graph.slides}
    {workspaceHrefBase}
    {selectedSlideId}
    {selectedSlideIds}
    {recommendationCounts}
    {findingSeverities}
    {isAddingSlide}
    {allowAddSlide}
    {onToggleSlideSelection}
    {onSelectSlide}
    {onSelectAll}
    {onClearSelection}
    {onAddSlide}
  />
{:else}
  <aside class="deck-left-panel panel">
    <div class="deck-left-panel__head">
      <div class="eyebrow">{activeTool.replaceAll('_', ' ')}</div>
      <h3>
        {#if activeTool === 'deck_map'}Deck map{/if}
        {#if activeTool === 'elements'}Elements{/if}
        {#if activeTool === 'text'}Text{/if}
        {#if activeTool === 'media'}Media{/if}
        {#if activeTool === 'data'}Data{/if}
        {#if activeTool === 'ai_tools'}AI Tools{/if}
        {#if activeTool === 'brand'}Brand{/if}
        {#if activeTool === 'settings'}Settings{/if}
      </h3>
    </div>

    {#if activeTool === 'deck_map'}
      <section class="deck-left-panel__section">
        <p class="muted">Use this map to understand how the current deck narrative is distributed before you create a new design version.</p>
        <div class="deck-left-panel__tag-grid">
          {#each topRoles as [role, count]}
            <span class="pill">{role.replaceAll('_', ' ')} · {count}</span>
          {/each}
        </div>
      </section>
    {/if}

    {#if activeTool === 'elements'}
      <section class="deck-left-panel__section">
        <p class="muted">These are the editable block types currently detected on the selected slide.</p>
        <div class="deck-left-panel__stack">
          {#each selectedBlocks as block}
            <article class="deck-left-panel__card">
              <strong>{block.blockType}</strong>
              <span>{block.rawText}</span>
            </article>
          {/each}
        </div>
      </section>
    {/if}

    {#if activeTool === 'text'}
      <section class="deck-left-panel__section">
        <p class="muted">The shell keeps text editing reviewable. Use Smart Edit for suggestion-based rewrites and this panel for content awareness.</p>
        <div class="deck-left-panel__stack">
          {#each textBlocks as block}
            <article class="deck-left-panel__card">
              <strong>{block.blockType}</strong>
              <span>{block.rawText}</span>
            </article>
          {/each}
        </div>
      </section>
    {/if}

    {#if activeTool === 'media'}
      <section class="deck-left-panel__section">
        <p class="muted">Media and brand assets attached during intake appear here so the editor stays tied to source material.</p>
        <div class="deck-left-panel__tag-grid">
          {#if properties?.sourceFileName}
            <span class="pill">Source deck · {properties.sourceFileName}</span>
          {/if}
          {#each properties?.brandAssetLabels ?? [] as label}
            <span class="pill">{label}</span>
          {/each}
        </div>
      </section>
    {/if}

    {#if activeTool === 'data'}
      <section class="deck-left-panel__section">
        <p class="muted">Data context combines metrics, content tags, and findings for the selected slide.</p>
        <div class="deck-left-panel__summary-grid">
          <article><span>Metrics</span><strong>{metricBlocks.length}</strong></article>
          <article><span>Content tags</span><strong>{selectedClassifications.length}</strong></article>
          <article><span>Findings</span><strong>{selectedFindings.length}</strong></article>
          <article><span>Recommendations</span><strong>{selectedSuggestions.length}</strong></article>
        </div>
      </section>
    {/if}

    {#if activeTool === 'ai_tools'}
      <section class="deck-left-panel__section">
        <p class="muted">AI tools stay review-first. Use the right-side design studio for iteration briefs and Smart Edit for block-level changes.</p>
        <div class="deck-left-panel__tag-grid">
          <span class="pill">Selected slides · {selectedSlideIds.length}</span>
          <span class="pill">Current slide · {selectedSlide?.title ?? 'None'}</span>
        </div>
      </section>
    {/if}

    {#if activeTool === 'brand'}
      <section class="deck-left-panel__section">
        <p class="muted">Brand context is loaded from the uploaded deck, company website, and any attached brand files.</p>
        <div class="deck-left-panel__stack">
          <article class="deck-left-panel__card">
            <strong>Company</strong>
            <span>{properties?.companyName ?? graph.deck.title}</span>
          </article>
          <article class="deck-left-panel__card">
            <strong>Website</strong>
            <span>{properties?.companyWebsiteUrl ?? 'Not connected yet'}</span>
          </article>
          <article class="deck-left-panel__card">
            <strong>Visual direction</strong>
            <span>{properties?.visualDirection ?? 'No visual direction saved yet'}</span>
          </article>
        </div>
      </section>
    {/if}

    {#if activeTool === 'settings'}
      <section class="deck-left-panel__section">
        <p class="muted">Shell settings should control how this workspace opens and which editing context is restored on return.</p>
        <div class="deck-left-panel__summary-grid">
          <article><span>Tool restore</span><strong>Enabled</strong></article>
          <article><span>Left panel</span><strong>Saved per deck</strong></article>
        </div>
      </section>
    {/if}
  </aside>
{/if}

<style>
  .deck-left-panel {
    display: grid;
    gap: 1rem;
    align-content: start;
    max-height: calc(100vh - 2rem);
    overflow: auto;
    padding: 1rem;
  }

  .deck-left-panel__head h3 {
    margin: 0.25rem 0 0;
  }

  .deck-left-panel__section {
    display: grid;
    gap: 0.85rem;
  }

  .deck-left-panel__stack,
  .deck-left-panel__tag-grid,
  .deck-left-panel__summary-grid {
    display: grid;
    gap: 0.75rem;
  }

  .deck-left-panel__tag-grid {
    grid-template-columns: repeat(auto-fit, minmax(120px, max-content));
  }

  .deck-left-panel__summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .deck-left-panel__card,
  .deck-left-panel__summary-grid article {
    border: 1px solid var(--line);
    border-radius: 18px;
    background: var(--surface-soft);
    padding: 0.9rem;
    display: grid;
    gap: 0.4rem;
  }

  .deck-left-panel__card span,
  .deck-left-panel__summary-grid span {
    color: var(--muted);
  }

  @media (max-width: 1320px) {
    .deck-left-panel {
      max-height: none;
    }
  }
 </style>
