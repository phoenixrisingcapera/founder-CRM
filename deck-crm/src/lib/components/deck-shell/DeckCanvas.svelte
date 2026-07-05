<script lang="ts">
  import type { BlockClassification, Deck, DeckSlide, DeckSlideBlock } from '$types/domain';

  interface Props {
    deck: Deck;
    mode: 'play' | 'edit' | 'preview';
    workspaceHrefBase?: string;
    selectedSlide?: DeckSlide;
    selectedBlocks: DeckSlideBlock[];
    selectedBlockId?: string;
    selectedSuggestionsCount: number;
    classificationLookup: Record<string, BlockClassification | undefined>;
    thumbnailSlides: DeckSlide[];
    onSelectBlock?: (blockId: string) => void;
    onSelectSlide?: (slideId: string) => void;
  }

  let {
    deck,
    mode,
    workspaceHrefBase = `/decks/${deck.id}/smart-deck`,
    selectedSlide,
    selectedBlocks,
    selectedBlockId,
    selectedSuggestionsCount,
    classificationLookup,
    thumbnailSlides,
    onSelectBlock,
    onSelectSlide
  }: Props = $props();

  function titleBlockForSlide() {
    return selectedBlocks.find((block) => ['headline', 'title'].includes(block.blockType));
  }

  function bodyBlocksForSlide() {
    return selectedBlocks.filter((block) => ['body', 'bullet', 'quote'].includes(block.blockType)).slice(0, 3);
  }

  function metricBlocksForSlide() {
    return selectedBlocks.filter((block) => block.blockType === 'metric').slice(0, 3);
  }

  function toneClassFor(slide?: DeckSlide) {
    if (!slide) return 'tone-default';

    const tones: Record<string, string> = {
      cover: 'tone-cover',
      problem: 'tone-problem',
      market: 'tone-market',
      solution: 'tone-solution',
      product: 'tone-product',
      traction: 'tone-traction',
      team: 'tone-team'
    };

    return tones[slide.role] ?? 'tone-default';
  }

  function classificationLabel(blockId: string) {
    const classification = classificationLookup[blockId];

    if (!classification) return 'Content tag pending';

    return `${classification.semanticTag} · ${classification.diligenceCategory}`;
  }
</script>

<section class="deck-canvas panel">
  <div class="deck-canvas__toolbar">
    <div class="deck-canvas__toolbar-group">
      <span class="pill">Deck file: {deck.file?.filename ?? 'Pending source file'}</span>
      <span class="pill">Mode · {mode}</span>
    </div>
    <div class="deck-canvas__toolbar-group">
      <span class="pill">Audience · {deck.audience}</span>
      <span class="pill">Purpose · {deck.purpose}</span>
    </div>
  </div>

  {#if selectedSlide}
    {@const heroBlock = titleBlockForSlide()}
    {@const bodyBlocks = bodyBlocksForSlide()}
    {@const metricBlocks = metricBlocksForSlide()}
    <article class="deck-canvas__card">
      <button
        type="button"
        class="deck-canvas__head"
        class:deck-canvas__selectable={Boolean(heroBlock)}
        class:selected={heroBlock && heroBlock.id === selectedBlockId}
        onclick={() => {
          if (heroBlock) onSelectBlock?.(heroBlock.id);
        }}
      >
        <div>
          <div class="eyebrow">Smart Deck</div>
          <h2>{heroBlock?.rawText ?? selectedSlide.title}</h2>
          <p class="muted">{selectedSlide.narrativeNotes || selectedSlide.rawText}</p>
        </div>
        <div class="deck-canvas__status">
          <span class="pill">Slide {String(selectedSlide.slideIndex).padStart(2, '0')}</span>
          <span class="pill">{selectedSlide.role.replaceAll('_', ' ')}</span>
        </div>
      </button>

      <div class="deck-canvas__grid">
        <div class="deck-canvas__story">
          {#each bodyBlocks as block}
            <button
              type="button"
              class="deck-canvas__story-block"
              class:selected={block.id === selectedBlockId}
              onclick={() => onSelectBlock?.(block.id)}
            >
              <strong>{classificationLabel(block.id)}</strong>
              <p>{block.rawText}</p>
            </button>
          {/each}
        </div>

        <div class="deck-canvas__visual">
          <div class={`deck-canvas__visual-stage ${toneClassFor(selectedSlide)}`}>
            <div class="deck-canvas__visual-card">
              <strong>{selectedSlide.title}</strong>
              <span>{selectedSlide.role.replaceAll('_', ' ')}</span>
            </div>
            <div class="deck-canvas__visual-card deck-canvas__visual-card--accent">
              <strong>{selectedSuggestionsCount}</strong>
              <span>audience recommendations</span>
            </div>
          </div>
        </div>
      </div>

      {#if metricBlocks.length > 0}
        <div class="deck-canvas__metrics">
          {#each metricBlocks as block}
            <button
              type="button"
              class="deck-canvas__metric-card"
              class:selected={block.id === selectedBlockId}
              onclick={() => onSelectBlock?.(block.id)}
            >
              <strong>{block.rawText}</strong>
              <span>{classificationLabel(block.id)}</span>
            </button>
          {/each}
        </div>
      {/if}
    </article>

    <div class="deck-canvas__thumbnail-strip">
      {#each thumbnailSlides as slide}
        <a
          class:selected={slide.id === selectedSlide.id}
          class="deck-canvas__thumbnail"
          href={`${workspaceHrefBase}?slide=${slide.id}`}
          onclick={() => onSelectSlide?.(slide.id)}
        >
          <span>{String(slide.slideIndex).padStart(2, '0')}</span>
          <strong>{slide.title}</strong>
        </a>
      {/each}
    </div>
  {/if}
</section>

<style>
  .deck-canvas {
    padding: 1rem;
    display: grid;
    gap: 1rem;
  }

  .deck-canvas__toolbar,
  .deck-canvas__head {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .deck-canvas__toolbar-group,
  .deck-canvas__status {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
  }

  .deck-canvas__card {
    border: 1px solid var(--line);
    border-radius: 28px;
    background: linear-gradient(180deg, var(--surface-input-strong), var(--surface));
    padding: clamp(1rem, 2vw, 1.6rem);
    display: grid;
    gap: 1.25rem;
    min-height: 720px;
  }

  .deck-canvas__head h2 {
    margin: 0.35rem 0 0.5rem;
    max-width: 18ch;
    font-size: clamp(2rem, 3.8vw, 4.25rem);
    letter-spacing: -0.06em;
    line-height: 0.94;
  }

  .deck-canvas__head p {
    max-width: 56ch;
    margin: 0;
  }

  .deck-canvas__head {
    border: 0;
    width: 100%;
    background: transparent;
    text-align: left;
    padding: 0;
    color: inherit;
  }

  .deck-canvas__grid {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
    gap: 1rem;
    align-items: stretch;
  }

  .deck-canvas__story,
  .deck-canvas__metrics {
    display: grid;
    gap: 0.85rem;
  }

  .deck-canvas__story-block,
  .deck-canvas__metric-card {
    border: 1px solid var(--line);
    border-radius: 22px;
    background: var(--surface-soft);
    padding: 1rem;
    text-align: left;
    color: inherit;
    width: 100%;
  }

  .deck-canvas__selectable,
  .deck-canvas__story-block,
  .deck-canvas__metric-card {
    cursor: pointer;
    transition: border-color 140ms ease, transform 140ms ease, background 140ms ease;
  }

  .deck-canvas__selectable.selected,
  .deck-canvas__story-block.selected,
  .deck-canvas__metric-card.selected {
    border-color: var(--line-strong);
    background: var(--surface-active);
    box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent);
  }

  .deck-canvas__selectable:hover,
  .deck-canvas__story-block:hover,
  .deck-canvas__metric-card:hover {
    transform: translateY(-1px);
  }

  .deck-canvas__story-block strong,
  .deck-canvas__metric-card span {
    color: var(--muted);
  }

  .deck-canvas__story-block p {
    margin: 0.55rem 0 0;
    line-height: 1.6;
  }

  .deck-canvas__visual-stage {
    min-height: 100%;
    border-radius: 24px;
    padding: 1rem;
    display: grid;
    grid-template-rows: minmax(0, 1fr) auto;
    gap: 0.85rem;
    border: 1px solid var(--line);
    background:
      radial-gradient(circle at top left, var(--accent-soft), transparent 32%),
      linear-gradient(180deg, var(--surface-soft), var(--surface-input));
  }

  .deck-canvas__visual-card {
    align-self: end;
    border: 1px solid var(--line);
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.72);
    color: #111827;
    padding: 1rem;
    display: grid;
    gap: 0.35rem;
  }

  :global([data-theme='dark']) .deck-canvas__visual-card {
    background: rgba(255, 255, 255, 0.88);
  }

  .deck-canvas__visual-card--accent {
    width: fit-content;
    min-width: 180px;
  }

  .deck-canvas__thumbnail-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.75rem;
  }

  .deck-canvas__thumbnail {
    border: 1px solid var(--line);
    border-radius: 18px;
    background: var(--surface-soft);
    padding: 0.85rem;
    display: grid;
    gap: 0.35rem;
  }

  .deck-canvas__thumbnail.selected {
    border-color: var(--line-strong);
    background: var(--surface-active);
  }

  .deck-canvas__thumbnail span {
    color: var(--muted);
    font-size: 0.82rem;
  }

  .tone-cover {
    background:
      radial-gradient(circle at top left, rgba(124, 58, 237, 0.25), transparent 40%),
      linear-gradient(180deg, var(--surface-input), var(--surface-soft));
  }

  .tone-problem {
    background:
      radial-gradient(circle at top right, rgba(255, 62, 165, 0.2), transparent 42%),
      linear-gradient(180deg, var(--surface-input), var(--surface-soft));
  }

  .tone-market,
  .tone-solution,
  .tone-product,
  .tone-traction,
  .tone-team,
  .tone-default {
    background:
      radial-gradient(circle at top left, rgba(0, 183, 255, 0.16), transparent 38%),
      linear-gradient(180deg, var(--surface-input), var(--surface-soft));
  }

  @media (max-width: 1080px) {
    .deck-canvas__card {
      min-height: auto;
    }

    .deck-canvas__grid {
      grid-template-columns: 1fr;
    }
  }
</style>
