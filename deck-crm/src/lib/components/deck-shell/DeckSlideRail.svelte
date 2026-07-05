<script lang="ts">
  import type { DeckSlide } from '$types/domain';

  interface Props {
    deckId: string;
    slides: DeckSlide[];
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
    deckId,
    slides,
    workspaceHrefBase = `/decks/${deckId}/smart-deck`,
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

  function toneClassFor(slide: DeckSlide) {
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

  function slideImageUrl(slide: DeckSlide) {
    return slide.previewUrl ?? slide.previewImageUrl ?? slide.thumbnailUrl ?? null;
  }
</script>

<aside class="deck-slide-rail panel">
  <div class="deck-slide-rail__head">
    <div>
      <div class="eyebrow">Slide navigator</div>
      <h3>{slides.length} slides</h3>
    </div>
    <button type="button" class="button secondary deck-slide-rail__mini-button" onclick={() => onSelectAll?.()}>
      Select all
    </button>
  </div>

  <div class="deck-slide-rail__actions">
    <button type="button" class="deck-slide-rail__text-action" onclick={() => onClearSelection?.()}>Clear</button>
    <span class="muted">{selectedSlideIds.length} selected</span>
  </div>

  {#if allowAddSlide}
    <button type="button" class="button deck-slide-rail__add-button" onclick={() => onAddSlide?.()} disabled={isAddingSlide}>
      {isAddingSlide ? 'Adding slide...' : 'Add slide'}
    </button>
  {/if}

  <div class="deck-slide-rail__list">
    {#each slides as slide}
      {@const imageUrl = slideImageUrl(slide)}
      <div class="deck-slide-rail__row">
        <button
          type="button"
          class:selected={selectedSlideIds.includes(slide.id)}
          class="deck-slide-rail__checkbox"
          aria-label={`Select ${slide.title}`}
          onclick={() => {
            onToggleSlideSelection?.(slide.id);
          }}
        >
          {selectedSlideIds.includes(slide.id) ? '✓' : ''}
        </button>

        <a
          class:selected={slide.id === selectedSlideId}
          class="deck-slide-rail__link"
          href={`${workspaceHrefBase}?slide=${slide.id}`}
          onclick={() => onSelectSlide?.(slide.id)}
        >
          <div class:has-image={Boolean(imageUrl)} class={`deck-slide-rail__thumb ${toneClassFor(slide)}`}>
            {#if imageUrl}
              <img src={imageUrl} alt="" loading="lazy" />
            {:else}
              <div class="deck-slide-rail__thumb-line deck-slide-rail__thumb-line--wide"></div>
              <div class="deck-slide-rail__thumb-line"></div>
              <div class="deck-slide-rail__thumb-bar"></div>
            {/if}
          </div>

          <div class="deck-slide-rail__copy">
            <div class="deck-slide-rail__meta">
              <strong>{String(slide.slideIndex).padStart(2, '0')}</strong>
              <span>{slide.title}</span>
            </div>
            <small>{slide.role.replaceAll('_', ' ')}</small>
            <div class="deck-slide-rail__foot">
              <span>{recommendationCounts[slide.id] ?? 0} recommendations</span>
              {#if findingSeverities[slide.id]}
                <span>{findingSeverities[slide.id]} risk</span>
              {/if}
            </div>
          </div>
        </a>
      </div>
    {/each}
  </div>
</aside>

<style>
  .deck-slide-rail {
    display: grid;
    gap: 0.9rem;
    align-content: start;
    max-height: calc(100vh - 2rem);
    overflow: auto;
    padding: 1rem;
  }

  .deck-slide-rail__head,
  .deck-slide-rail__actions {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .deck-slide-rail__head h3 {
    margin: 0.25rem 0 0;
  }

  .deck-slide-rail__mini-button {
    padding: 0.55rem 0.8rem;
  }

  .deck-slide-rail__text-action {
    border: 0;
    background: transparent;
    color: var(--accent);
    padding: 0;
  }

  .deck-slide-rail__list {
    display: grid;
    gap: 0.75rem;
  }

  .deck-slide-rail__add-button {
    width: 100%;
    justify-content: center;
  }

  .deck-slide-rail__row {
    display: grid;
    grid-template-columns: 32px minmax(0, 1fr);
    gap: 0.8rem;
    align-items: start;
  }

  .deck-slide-rail__checkbox {
    width: 32px;
    height: 32px;
    border-radius: 12px;
    border: 1px solid var(--line);
    background: var(--surface-input);
    color: var(--ink);
  }

  .deck-slide-rail__checkbox.selected {
    border-color: var(--line-strong);
    background: var(--accent);
    color: var(--button-primary-ink);
  }

  .deck-slide-rail__link {
    display: grid;
    grid-template-columns: 78px minmax(0, 1fr);
    gap: 0.8rem;
    border: 1px solid transparent;
    border-radius: 20px;
    background: var(--surface-soft);
    padding: 0.75rem;
    transition: border-color 160ms ease, transform 160ms ease;
  }

  .deck-slide-rail__link.selected {
    border-color: var(--line-strong);
    background: linear-gradient(135deg, var(--surface-active), rgba(124, 58, 237, 0.16));
    transform: translateY(-1px);
  }

  .deck-slide-rail__thumb {
    min-height: 56px;
    border-radius: 16px;
    border: 1px solid var(--line);
    padding: 0.75rem;
    display: grid;
    gap: 0.45rem;
    background: linear-gradient(180deg, var(--surface-input), var(--surface-soft));
    overflow: hidden;
  }

  .deck-slide-rail__thumb.has-image {
    padding: 0;
    background: #020617;
  }

  .deck-slide-rail__thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .deck-slide-rail__thumb-line,
  .deck-slide-rail__thumb-bar {
    border-radius: 999px;
    background: color-mix(in srgb, var(--ink-strong) 72%, transparent);
  }

  :global([data-theme='light']) .deck-slide-rail__thumb-line,
  :global([data-theme='light']) .deck-slide-rail__thumb-bar {
    background: rgba(6, 18, 38, 0.18);
  }

  .deck-slide-rail__thumb-line {
    height: 8px;
    width: 70%;
  }

  .deck-slide-rail__thumb-line--wide {
    width: 88%;
  }

  .deck-slide-rail__thumb-bar {
    height: 18px;
    width: 48%;
  }

  .deck-slide-rail__copy {
    min-width: 0;
    display: grid;
    gap: 0.3rem;
  }

  .deck-slide-rail__meta {
    display: flex;
    gap: 0.45rem;
    align-items: baseline;
  }

  .deck-slide-rail__meta span {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .deck-slide-rail__meta span,
  .deck-slide-rail__copy small,
  .deck-slide-rail__foot {
    color: var(--muted);
  }

  .deck-slide-rail__foot {
    display: flex;
    gap: 0.55rem;
    flex-wrap: wrap;
    font-size: 0.78rem;
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
    .deck-slide-rail {
      max-height: none;
    }
  }
</style>
