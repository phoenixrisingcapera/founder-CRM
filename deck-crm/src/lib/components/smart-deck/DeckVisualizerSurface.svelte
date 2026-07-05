<script lang="ts">
  import GeneratedSlideRenderer from './GeneratedSlideRenderer.svelte';
  import type { RenderSchema } from '$lib/api/smartDeckWorkspace';

  type VisualizerSlide = {
    title: string;
    slideIndex?: number | null;
    slideNumber?: number | null;
    role?: string | null;
    previewImageUrl?: string | null;
    previewUrl?: string | null;
    thumbnailUrl?: string | null;
    extractedText?: string | null;
    rawText?: string | null;
  };

  interface Props {
    title: string;
    subtitle?: string;
    slide?: VisualizerSlide | null;
    renderSchema?: RenderSchema | null;
    designTokens?: Record<string, string> | null;
    selectedElementId?: string | null;
    onSelectElement?: (elementId: string) => void;
    emptyTitle?: string;
    emptyText?: string;
  }

  let {
    title,
    subtitle = '',
    slide = null,
    renderSchema = null,
    designTokens = null,
    selectedElementId = null,
    onSelectElement,
    emptyTitle = 'No slide available',
    emptyText = 'Select a slide to load the shared visualizer surface.'
  }: Props = $props();

  const slideLabel = $derived(
    slide ? `Slide ${String(slide.slideIndex ?? slide.slideNumber ?? 0).padStart(2, '0')}` : 'No slide selected'
  );
  const slideTitle = $derived(slide?.title ?? emptyTitle);
  const slideSource = $derived(slide ? slideImageUrl(slide) : null);
  const hasRenderableSchema = $derived(Boolean(renderSchema?.elements?.length));

  function slideImageUrl(currentSlide: VisualizerSlide) {
    const url = currentSlide.previewImageUrl ?? currentSlide.previewUrl ?? currentSlide.thumbnailUrl ?? null;
    if (!url) return null;
    if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('/') || url.startsWith('data:')) {
      return url;
    }
    return `/${url}`;
  }
</script>

<article class="panel deck-visualizer-surface">
  <header class="surface-header">
    <div>
      <div class="eyebrow">Reusable visualizer</div>
      <h3>{title}</h3>
      {#if subtitle}
        <p>{subtitle}</p>
      {/if}
    </div>
    <span class="surface-pill">{slideLabel}</span>
  </header>

  <div class="surface-frame">
    {#if hasRenderableSchema}
      <GeneratedSlideRenderer
        renderSchema={renderSchema}
        designTokens={designTokens}
        selectedElementId={selectedElementId}
        {onSelectElement}
      />
    {:else if slide}
      {#if slideSource}
        <img src={slideSource} alt="" loading="lazy" />
      {:else}
        <div class="surface-empty">
          <strong>{slideTitle}</strong>
          <p>{slide.extractedText || slide.rawText || emptyText}</p>
        </div>
      {/if}
    {:else}
      <div class="surface-empty">
        <strong>{emptyTitle}</strong>
        <p>{emptyText}</p>
      </div>
    {/if}
  </div>

  {#if slide}
    <footer class="surface-footer">
      <div>
        <span class="muted">Title</span>
        <strong>{slide.title}</strong>
      </div>
      <div>
        <span class="muted">Role</span>
        <strong>{slide.role}</strong>
      </div>
      <div>
        <span class="muted">Preview</span>
        <strong>{slide.previewImageUrl || slide.previewUrl || slide.thumbnailUrl ? 'Available' : 'Missing'}</strong>
      </div>
    </footer>
  {/if}
</article>

<style>
  .deck-visualizer-surface {
    display: grid;
    gap: 0.9rem;
    padding: 1rem;
    min-width: 0;
  }

  .surface-header,
  .surface-footer {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .surface-header h3 {
    margin: 0.25rem 0 0;
  }

  .surface-header p {
    margin: 0.3rem 0 0;
    color: var(--muted);
  }

  .surface-pill {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 0.45rem 0.75rem;
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.04);
    white-space: nowrap;
  }

  .surface-frame {
    min-height: 320px;
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.02);
  }

  .surface-frame :global(.render-stage),
  .surface-frame :global(.render-empty) {
    width: 100%;
    min-height: 320px;
  }

  .surface-frame img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
    background: rgba(0, 0, 0, 0.16);
  }

  .surface-empty {
    min-height: 320px;
    display: grid;
    align-content: center;
    justify-items: start;
    gap: 0.35rem;
    padding: 1.2rem;
  }

  .surface-empty p {
    margin: 0;
    color: var(--muted);
  }

  .surface-footer {
    align-items: stretch;
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 0.1rem;
  }

  .surface-footer > div {
    min-width: 0;
    flex: 1 1 0;
  }
</style>
