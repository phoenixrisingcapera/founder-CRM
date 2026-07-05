<script lang="ts">
  import type { SmartDeckSourceSlide } from '$lib/api/smartDeckWorkspace';

  interface Props {
    sourcePdfSlides?: SmartDeckSourceSlide[];
    selectedSourceSlideIds?: string[];
    activeSourceSlideId?: string | null;
    onToggleSlide?: (slideId: string) => void;
    onSetActiveSlide?: (slideId: string) => void;
    onSelectAll?: () => void;
    onClearSelection?: () => void;
  }

  let {
    sourcePdfSlides = [],
    selectedSourceSlideIds = [],
    activeSourceSlideId = null,
    onToggleSlide,
    onSetActiveSlide,
    onSelectAll,
    onClearSelection
  }: Props = $props();

  function isSelected(slideId: string) {
    return selectedSourceSlideIds.includes(slideId);
  }

  function slideLabel(slideNumber: number) {
    return `Slide ${String(slideNumber).padStart(2, '0')}`;
  }

  function slideImageUrl(slide: SmartDeckSourceSlide) {
    const url = slide.previewImageUrl ?? slide.thumbnailUrl ?? null;
    if (!url) return null;
    if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('/') || url.startsWith('data:')) return url;
    return `/${url}`;
  }
</script>

<article class="panel pdf-slide-miniatures-card">
  <header class="card-header">
    <div>
      <div class="eyebrow">Uploaded deck</div>
      <h2>Source PDF slides</h2>
    </div>
    <span class="pill">{selectedSourceSlideIds.length} selected</span>
  </header>

  <div class="selection-actions">
    <button type="button" onclick={() => onSelectAll?.()} disabled={sourcePdfSlides.length === 0}>Select all</button>
    <button type="button" onclick={() => onClearSelection?.()} disabled={selectedSourceSlideIds.length === 0}>Clear selection</button>
  </div>

  <div class="miniature-strip" aria-label="Original uploaded PDF slides">
    {#each sourcePdfSlides as slide}
      {@const imageUrl = slideImageUrl(slide)}
      <article class:selected={isSelected(slide.id)} class:active={activeSourceSlideId === slide.id}>
        <button type="button" class="miniature-main" onclick={() => onSetActiveSlide?.(slide.id)}>
        <div class:has-image={Boolean(imageUrl)} class="miniature-canvas">
          {#if imageUrl}
            <img src={imageUrl} alt="" loading="lazy" />
          {:else}
            <span>{slide.slideNumber}</span>
            <strong>{slide.title}</strong>
            <p>{slide.extractedText || 'Source slide content'}</p>
          {/if}
        </div>
        </button>
        <div class="miniature-footer">
          <label>
            <input
              type="checkbox"
              checked={isSelected(slide.id)}
              onchange={() => onToggleSlide?.(slide.id)}
            />
            <span>{isSelected(slide.id) ? 'Selected' : 'Select for generation'}</span>
          </label>
          <small>{slideLabel(slide.slideNumber)}</small>
        </div>
      </article>
    {/each}
  </div>
</article>

<style>
  .pdf-slide-miniatures-card {
    min-height: 0;
    height: 100%;
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr);
    gap: 0.85rem;
    padding: 0.85rem;
    overflow: hidden;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
    flex-wrap: wrap;
  }

  .selection-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
  }

  .selection-actions button {
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-soft);
    color: inherit;
    padding: 0.45rem 0.7rem;
  }

  .selection-actions button:disabled {
    opacity: 0.55;
  }

  h2 {
    margin: 0;
  }

  .miniature-strip {
    display: grid;
    grid-auto-rows: min-content;
    gap: 0.72rem;
    overflow-y: auto;
    padding-right: 0.1rem;
  }

  .miniature-strip article {
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-soft);
    color: inherit;
    padding: 0.7rem;
    display: grid;
    gap: 0.65rem;
    text-align: left;
  }

  .miniature-strip article.selected {
    border-color: var(--line-strong);
    background: var(--surface-active);
  }

  .miniature-strip article.active {
    box-shadow: inset 0 0 0 2px var(--line-contrast);
  }

  .miniature-main {
    display: block;
    border: 0;
    background: transparent;
    color: inherit;
    padding: 0;
    text-align: left;
  }

  .miniature-canvas {
    aspect-ratio: 16 / 9;
    border-radius: 8px;
    background: var(--surface-input-strong);
    color: var(--ink);
    padding: 0.7rem;
    display: grid;
    gap: 0.35rem;
    align-content: start;
    overflow: hidden;
  }

  .miniature-canvas.has-image {
    padding: 0;
    background: var(--surface-strong);
  }

  .miniature-canvas img {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: cover;
  }

  .miniature-canvas span {
    color: var(--muted);
    font-size: 0.72rem;
  }

  .miniature-canvas strong {
    font-size: 0.9rem;
    line-height: 1.2;
  }

  .miniature-canvas p {
    margin: 0;
    color: var(--muted);
    font-size: 0.74rem;
    line-height: 1.25;
  }

  .miniature-footer {
    display: grid;
    gap: 0.25rem;
  }

  .miniature-footer label {
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }

  .miniature-footer span,
  .miniature-footer small {
    color: var(--muted);
  }

  @media (max-width: 1180px) {
    .pdf-slide-miniatures-card {
      max-height: 22rem;
    }

    .miniature-strip {
      grid-auto-flow: column;
      grid-auto-columns: minmax(12rem, 15rem);
      overflow-x: auto;
      overflow-y: hidden;
      padding-bottom: 0.2rem;
    }
  }
</style>
