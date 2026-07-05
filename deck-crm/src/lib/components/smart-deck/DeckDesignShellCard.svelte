<script lang="ts">
  import type { GeneratedSlide } from '@deck-aistack-codes/shared';
  import type { GeneratedSlideCode, RenderSchema, SmartDeckGenerationStatus, SmartDeckSourceSlide } from '$lib/api/smartDeckWorkspace';
  import InfoBubble from './InfoBubble.svelte';
  import DeckVisualizerSurface from './DeckVisualizerSurface.svelte';

  type DesignViewMode = 'current' | 'preview' | 'compare';

  interface Props {
    activeBatchId?: string | null;
    generatedSlides?: GeneratedSlide[];
    currentGeneratedSlides?: GeneratedSlide[];
    previewGeneratedSlides?: GeneratedSlide[];
    activeGeneratedSlideId?: string | null;
    currentGeneratedSlideId?: string | null;
    previewGeneratedSlideId?: string | null;
    activeSourceSlide?: SmartDeckSourceSlide | null;
    generationStatus?: SmartDeckGenerationStatus;
    generatedSlideCode?: GeneratedSlideCode | null;
    currentGeneratedSlideCode?: GeneratedSlideCode | null;
    previewGeneratedSlideCode?: GeneratedSlideCode | null;
    currentRenderSchema?: RenderSchema | null;
    previewRenderSchema?: RenderSchema | null;
    activeRenderSchema?: RenderSchema | null;
    designViewMode?: DesignViewMode;
    hasPreviewDesign?: boolean;
    selectedElementId?: string | null;
    selectedGeneratedElementId?: string | null;
    onSelectGeneratedSlide?: (slideId: string) => void;
    onSelectElement?: (elementId: string) => void;
    onShowCurrent?: () => void;
    onShowPreview?: () => void;
    onShowCompare?: () => void;
  }

  let {
    activeBatchId = null,
    generatedSlides = [],
    currentGeneratedSlides = [],
    previewGeneratedSlides = [],
    activeGeneratedSlideId = null,
    currentGeneratedSlideId = null,
    previewGeneratedSlideId = null,
    activeSourceSlide = null,
    generationStatus = 'idle',
    generatedSlideCode = null,
    currentGeneratedSlideCode = null,
    previewGeneratedSlideCode = null,
    currentRenderSchema = null,
    previewRenderSchema = null,
    activeRenderSchema = null,
    designViewMode = 'current',
    hasPreviewDesign = false,
    selectedElementId = null,
    selectedGeneratedElementId = null,
    onSelectGeneratedSlide,
    onSelectElement,
    onShowCurrent,
    onShowPreview,
    onShowCompare
  }: Props = $props();

  const currentGeneratedSlide = $derived(currentGeneratedSlides.find((slide) => slide.id === currentGeneratedSlideId) ?? currentGeneratedSlides[0] ?? null);
  const previewGeneratedSlide = $derived(previewGeneratedSlides.find((slide) => slide.id === previewGeneratedSlideId || slide.id === activeGeneratedSlideId) ?? previewGeneratedSlides[0] ?? generatedSlides.find((slide) => slide.id === activeGeneratedSlideId) ?? generatedSlides[0] ?? null);
  const activeGeneratedSlide = $derived(designViewMode === 'current' ? currentGeneratedSlide : previewGeneratedSlide);
  const selectedGeneratedElement = $derived(selectedGeneratedElementId ?? selectedElementId);
  const resolvedCurrentRenderSchema = $derived(currentRenderSchema ?? currentGeneratedSlideCode?.renderSchema ?? null);
  const resolvedPreviewRenderSchema = $derived(previewRenderSchema ?? (previewGeneratedSlideCode ?? generatedSlideCode)?.renderSchema ?? null);
  const resolvedCurrentDesignTokens = $derived(currentGeneratedSlideCode?.designTokens ?? null);
  const resolvedPreviewDesignTokens = $derived((previewGeneratedSlideCode ?? generatedSlideCode)?.designTokens ?? null);
  const resolvedActiveRenderSchema = $derived(
    activeRenderSchema ?? (designViewMode === 'current' ? resolvedCurrentRenderSchema : resolvedPreviewRenderSchema)
  );
  const resolvedActiveDesignTokens = $derived(
    designViewMode === 'current' ? resolvedCurrentDesignTokens : resolvedPreviewDesignTokens
  );
  const activeSlideCode = $derived(designViewMode === 'current' ? currentGeneratedSlideCode : (previewGeneratedSlideCode ?? generatedSlideCode));
  const visibleGeneratedSlides = $derived(designViewMode === 'current' ? currentGeneratedSlides : previewGeneratedSlides.length > 0 ? previewGeneratedSlides : generatedSlides);
  const isGenerating = $derived(generationStatus === 'running');

  function versionLabel() {
    if (!activeBatchId) return 'No active iteration';
    return 'Active iteration';
  }

  function generationLabel() {
    if (generationStatus === 'running') return 'Creating preview';
    if (hasPreviewDesign && designViewMode === 'preview') return 'Preview ready';
    if (hasPreviewDesign && designViewMode === 'compare') return 'Comparing versions';
    if (currentGeneratedSlides.length > 0) return 'Current deck';
    if (generatedSlides.length > 0) return 'Preview ready';
    return generationStatus.replaceAll('_', ' ');
  }
</script>

<article class="panel deck-design-shell-card">
  <header class="card-header">
    <div>
      <div class="eyebrow">Deck visualizer</div>
      <h2>Generated deck preview</h2>
    </div>
    <div class="card-header__tools">
      <div class="design-mode-switch" aria-label="Deck view mode">
        <button type="button" class:active={designViewMode === 'current'} onclick={() => onShowCurrent?.()}>Current</button>
        <button type="button" class:active={designViewMode === 'preview'} disabled={!hasPreviewDesign && !previewGeneratedSlide} onclick={() => onShowPreview?.()}>Preview</button>
        <button type="button" class:active={designViewMode === 'compare'} disabled={!hasPreviewDesign} onclick={() => onShowCompare?.()}>Compare</button>
      </div>
      <InfoBubble
        label="Generated deck preview help"
        text="Current shows the saved deck, Preview shows the candidate change, and Compare lets you review both before saving."
      />
      <span class="pill">{versionLabel()}</span>
    </div>
  </header>

  <div class="shell-frame" class:is-generating={isGenerating}>
    {#if isGenerating}
      <div class="generation-overlay" aria-live="polite">
        <strong>Creating editable slide</strong>
        <span>Reading selected slides and validating the scene graph.</span>
      </div>
    {/if}

    {#if designViewMode === 'compare' && resolvedCurrentRenderSchema && resolvedPreviewRenderSchema}
      <div class="compare-grid" aria-label="Compare current and preview slides">
        <section class="compare-panel">
          <div class="compare-label">
            <strong>Current</strong>
            <span>Saved deck</span>
          </div>
          <DeckVisualizerSurface
            title="Current deck"
            slide={activeSourceSlide}
            renderSchema={resolvedCurrentRenderSchema}
            designTokens={resolvedCurrentDesignTokens}
            selectedElementId={selectedGeneratedElement}
            {onSelectElement}
          />
        </section>
        <section class="compare-panel">
          <div class="compare-label">
            <strong>Preview</strong>
            <span>Candidate change</span>
          </div>
          <DeckVisualizerSurface
            title="Preview deck"
            slide={activeSourceSlide}
            renderSchema={resolvedPreviewRenderSchema}
            designTokens={resolvedPreviewDesignTokens}
            selectedElementId={selectedGeneratedElement}
            {onSelectElement}
          />
        </section>
      </div>
    {:else if activeGeneratedSlide && resolvedActiveRenderSchema}
      <div class="generated-slide-preview" class:is-preview={designViewMode === 'preview'}>
        <DeckVisualizerSurface
          title={designViewMode === 'preview' ? 'Preview deck' : 'Current deck'}
          slide={activeSourceSlide}
          renderSchema={resolvedActiveRenderSchema}
          designTokens={resolvedActiveDesignTokens}
          selectedElementId={selectedGeneratedElement}
          {onSelectElement}
        />
      </div>
    {:else if activeSourceSlide}
      <div class="source-slide-preview">
        <DeckVisualizerSurface
          title="Source slide"
          slide={activeSourceSlide}
          emptyTitle="No source slide available"
          emptyText="Select a source slide to inspect its preview."
        />
      </div>
    {:else}
      <div class="shell-empty">
        <div class="shell-empty__head">
          <strong>No generated slides yet</strong>
          <InfoBubble
            label="No generated slides help"
            text="Select source slides and send a prompt to have the LLM create your next iteration."
            side="right"
          />
        </div>
      </div>
    {/if}
  </div>

  <footer class="shell-footer">
    <div>
      <span class="muted">Generation</span>
      <strong>{generationLabel()}</strong>
    </div>
    <div>
      <span class="muted">Active source</span>
      <strong>{activeSourceSlide?.title ?? 'None'}</strong>
    </div>
    <div>
      <span class="muted">Slide quality</span>
      <strong>{activeSlideCode?.validationStatus === 'valid' ? 'Ready' : 'Needs review'}</strong>
    </div>
    <div>
      <span class="muted">Selected design element</span>
      <strong>{selectedGeneratedElement ? 'Selected' : 'None'}</strong>
    </div>
  </footer>

  {#if visibleGeneratedSlides.length > 0}
    <div class="generated-slide-strip" aria-label="Generated slides">
      {#each visibleGeneratedSlides as slide}
        <button
          type="button"
          class:active={slide.id === activeGeneratedSlide?.id}
          onclick={() => onSelectGeneratedSlide?.(slide.id)}
        >
          <span>{slide.slideType.replaceAll('_', ' ')}</span>
          <strong>{slide.title}</strong>
        </button>
      {/each}
    </div>
  {/if}
</article>

<style>
  .deck-design-shell-card {
    min-height: 0;
    height: 100%;
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto auto;
    gap: 1rem;
    padding: 1rem;
  }

  .card-header,
  .shell-footer {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
    flex-wrap: wrap;
  }

  .shell-footer {
    align-items: stretch;
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 0.15rem;
  }

  .shell-footer > div {
    min-width: 0;
    flex: 1 1 0;
  }

  .card-header__tools,
  .shell-empty__head {
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }

  .card-header__tools {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .design-mode-switch {
    display: flex;
    gap: 0.15rem;
    padding: 0.18rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-soft);
  }

  .design-mode-switch button {
    min-height: 2rem;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: var(--muted);
    padding: 0 0.65rem;
    font-weight: 700;
    cursor: pointer;
  }

  .design-mode-switch button.active {
    background: var(--surface);
    color: var(--ink);
    box-shadow: var(--shadow);
  }

  .design-mode-switch button:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  h2 {
    margin: 0;
  }

  .shell-frame {
    position: relative;
    min-height: 0;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-muted);
    display: grid;
    overflow: hidden;
  }

  .generated-slide-preview,
  .source-slide-preview,
  .shell-empty {
    min-height: 100%;
    display: grid;
    place-items: center;
    padding: 1rem;
  }

  .generated-slide-preview.is-preview {
    background: color-mix(in srgb, var(--accent-soft) 30%, transparent);
  }

  .compare-grid {
    min-height: 100%;
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 1rem;
    align-items: start;
    padding: 1rem;
  }

  .compare-panel {
    min-width: 0;
    display: grid;
    gap: 0.65rem;
    justify-items: center;
  }

  .compare-label {
    width: min(100%, 72rem);
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
    color: var(--muted);
  }

  .compare-label strong {
    color: var(--ink);
  }

  .generation-overlay {
    position: absolute;
    inset: 0;
    z-index: 3;
    display: grid;
    place-content: center;
    gap: 0.4rem;
    text-align: center;
    background: color-mix(in srgb, var(--surface) 76%, transparent);
    backdrop-filter: blur(10px);
  }

  .generation-overlay strong {
    font-size: 1rem;
  }

  .generation-overlay span {
    color: var(--muted);
  }

  .shell-empty {
    text-align: center;
  }

  .shell-empty__head {
    justify-content: center;
  }

  .shell-footer > div {
    display: grid;
    gap: 0.2rem;
  }

  .generated-slide-strip {
    display: grid;
    grid-auto-flow: column;
    grid-auto-columns: minmax(12rem, 1fr);
    gap: 0.65rem;
    overflow-x: auto;
  }

  .generated-slide-strip button {
    min-height: 4.5rem;
    border-radius: 8px;
    border: 1px solid var(--line);
    background: var(--surface-soft);
    color: inherit;
    display: grid;
    gap: 0.3rem;
    text-align: left;
    padding: 0.75rem;
  }

  .generated-slide-strip button.active {
    border-color: var(--line-strong);
    background: var(--surface-active);
  }

  .generated-slide-strip span,
  .muted {
    color: var(--muted);
  }

  @media (max-width: 900px) {
    .compare-grid {
      grid-template-columns: 1fr;
      align-content: start;
      overflow-y: auto;
    }

    .shell-footer {
      flex-wrap: wrap;
      overflow-x: visible;
    }

    .shell-footer > div {
      flex: 1 1 calc(50% - 0.4rem);
    }
  }
</style>
