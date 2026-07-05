<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import DeckVisualizerSurface from '$components/smart-deck/DeckVisualizerSurface.svelte';
  import type { RenderSchema } from '$lib/api/smartDeckWorkspace';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const payload = $derived(data.slides);
  let selectedSlideId = $state<string | null>(null);
  let selectedGeneratedId = $state<string | null>(null);
  let selectedElementId = $state<string | null>(null);

  const selectedSlide = $derived(payload.slides.find((slide) => slide.id === selectedSlideId) ?? payload.slides[0] ?? null);
  const generatedForSlide = $derived(selectedSlide?.generatedSlides ?? []);
  const selectedGenerated = $derived(
    generatedForSlide.find((slide) => slide.id === selectedGeneratedId) ?? generatedForSlide[0] ?? null
  );
  const selectedElement = $derived(
    selectedGenerated?.elements.find((element) => element.id === selectedElementId) ?? null
  );
  const countCards = $derived(Object.entries(payload.counts));

  function selectSlide(slideId: string) {
    selectedSlideId = slideId;
    const next = payload.slides.find((slide) => slide.id === slideId)?.generatedSlides[0] ?? null;
    selectedGeneratedId = next?.id ?? null;
    selectedElementId = null;
  }

  function label(value: string | null | undefined) {
    return value?.replaceAll('_', ' ').replaceAll(':', ' / ') ?? 'Unknown';
  }

  function statusTone(status: string) {
    const normalized = status.toLowerCase();
    if (['failed', 'failure', 'error', 'invalid'].includes(normalized)) return 'failed';
    if (['running', 'queued', 'pending', 'processing'].includes(normalized)) return 'running';
    if (['completed', 'success', 'ready', 'valid', 'draft', 'reviewed', 'applied'].includes(normalized)) return 'completed';
    return 'neutral';
  }

  function renderSchema(value: Record<string, unknown> | null | undefined) {
    return (value ?? null) as RenderSchema | null;
  }

  function designTokens(value: Record<string, string> | null | undefined) {
    return value ?? null;
  }

  function formatJson(value: unknown) {
    return JSON.stringify(value, null, 2);
  }
</script>

<AppShell
  title="Slide Inspector"
  subtitle="Read-only source and generated slide comparison for admin diagnostics."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="slides-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/failure-tickets">Failure tickets</a>
      <a href="/admin/users">Users</a>
      <a href={`/admin/processing/${encodeURIComponent(payload.deck.id)}`}>Processing</a>
      <a class="active" href={`/admin/slides/${encodeURIComponent(payload.deck.id)}`}>Slides</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
    </nav>

    <section class="deck-head panel">
      <div>
        <p class="eyebrow">Deck</p>
        <h2>{payload.deck.title}</h2>
        <p class="muted">
          {payload.deck.workspaceName ?? payload.deck.workspaceId ?? 'No workspace'} ·
          {payload.deck.userEmail ?? payload.deck.userId ?? 'No user'}
        </p>
      </div>
      <span class={`status ${statusTone(payload.deck.status)}`}>{label(payload.deck.status)}</span>
    </section>

    <section class="count-grid" aria-label="Slide inspector counts">
      {#each countCards as [key, value]}
        <article class="panel count-card">
          <span>{label(key)}</span>
          <strong>{value}</strong>
        </article>
      {/each}
    </section>

    <section class="inspector-grid">
      <aside class="panel slide-list" aria-label="Source slides">
        <p class="eyebrow">Source slides</p>
        <div class="slide-buttons">
          {#each payload.slides as slide}
            <button class:active={selectedSlide?.id === slide.id} type="button" onclick={() => selectSlide(slide.id)}>
              <span>{slide.slideNumber ?? slide.slideIndex}</span>
              <strong>{slide.title}</strong>
              <small>{slide.generatedSlides.length} generated · {slide.blockCount} blocks</small>
            </button>
          {:else}
            <p class="muted">No source slides recorded.</p>
          {/each}
        </div>
      </aside>

      <main class="panel preview-panel">
        {#if selectedSlide}
          <div class="preview-head">
            <div>
              <p class="eyebrow">Comparison</p>
              <h2>{selectedSlide.title}</h2>
            </div>
            <span class="status neutral">{selectedSlide.role}</span>
          </div>

          <section class="compare-grid">
            <article class="source-preview">
              <p class="eyebrow">Source</p>
              <h3>{selectedSlide.summary ?? selectedSlide.semanticSlideType ?? 'Source text preview'}</h3>
              <p>{selectedSlide.textPreview ?? 'No source text preview stored.'}</p>
            </article>

            <article class="generated-preview">
              <div class="generated-select">
                <label>
                  Generated version
                  <select bind:value={selectedGeneratedId}>
                    {#each generatedForSlide as generated}
                      <option value={generated.id}>{generated.title} · {generated.validationStatus}</option>
                    {/each}
                  </select>
                </label>
              </div>
              {#if selectedGenerated}
                <DeckVisualizerSurface
                  title="Generated slide"
                  subtitle="Admin slide inspector"
                  slide={selectedSlide}
                  renderSchema={renderSchema(selectedGenerated.renderSchema)}
                  designTokens={designTokens(selectedGenerated.designTokens)}
                  selectedElementId={selectedElementId}
                  onSelectElement={(elementId) => (selectedElementId = elementId)}
                />
              {:else}
                <div class="empty-render">No generated slide linked to this source slide.</div>
              {/if}
            </article>
          </section>
        {:else}
          <p class="muted">Select a slide to inspect.</p>
        {/if}
      </main>

      <aside class="panel meta-panel" aria-label="Slide metadata">
        <p class="eyebrow">Metadata</p>
        {#if selectedSlide}
          <h2>Slide records</h2>
          <dl>
            <div><dt>Source slide ID</dt><dd>{selectedSlide.id}</dd></div>
            <div><dt>Blocks</dt><dd>{selectedSlide.blocks.length}</dd></div>
            <div><dt>Assets</dt><dd>{selectedSlide.assets.length}</dd></div>
            <div><dt>Generated</dt><dd>{generatedForSlide.length}</dd></div>
            {#if selectedGenerated}
              <div><dt>Generated slide ID</dt><dd>{selectedGenerated.id}</dd></div>
              <div><dt>Design version</dt><dd>{selectedGenerated.designVersionId}</dd></div>
              <div><dt>Validation</dt><dd>{selectedGenerated.validationStatus}</dd></div>
              <div><dt>Elements</dt><dd>{selectedGenerated.elementCount}</dd></div>
            {/if}
          </dl>

          <h3>Blocks</h3>
          <pre>{formatJson(selectedSlide.blocks)}</pre>

          <h3>Selected element</h3>
          <pre>{formatJson(selectedElement ?? selectedGenerated?.elements[0] ?? null)}</pre>
        {:else}
          <p class="muted">No selected slide.</p>
        {/if}
      </aside>
    </section>

    <section class="panel redaction-panel">
      <div>
        <p class="eyebrow">Redaction</p>
        <h2>Safe admin view</h2>
        <p>{payload.redaction.detailPolicy}</p>
      </div>
      <div class="redacted-list" aria-label="Redacted fields">
        {#each payload.redaction.sensitiveFieldsRedacted as field}
          <span>{field}</span>
        {/each}
      </div>
    </section>
  </section>
</AppShell>

<style>
  .slides-page {
    display: grid;
    gap: 1rem;
  }

  .admin-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .admin-tabs a {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.55rem 0.75rem;
    color: var(--text-muted);
    text-decoration: none;
    background: var(--surface-subtle);
  }

  .admin-tabs a.active {
    color: var(--text);
    border-color: var(--accent);
  }

  .deck-head,
  .inspector-grid,
  .compare-grid,
  .redaction-panel {
    display: grid;
    gap: 1rem;
  }

  .deck-head {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
    padding: 1rem;
  }

  .deck-head h2,
  .deck-head p,
  .preview-head h2,
  .preview-head p,
  .source-preview h3,
  .source-preview p,
  .meta-panel h2,
  .meta-panel h3,
  .meta-panel p,
  .redaction-panel h2,
  .redaction-panel p {
    margin: 0;
  }

  .count-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.75rem;
  }

  .count-card,
  .slide-list,
  .preview-panel,
  .meta-panel,
  .redaction-panel {
    padding: 1rem;
  }

  .count-card {
    display: grid;
    gap: 0.35rem;
  }

  .count-card span {
    color: var(--text-muted);
  }

  .count-card strong {
    font-size: 1.5rem;
  }

  .inspector-grid {
    grid-template-columns: minmax(220px, 0.75fr) minmax(0, 1.8fr) minmax(280px, 0.95fr);
    align-items: start;
  }

  .slide-buttons {
    display: grid;
    gap: 0.5rem;
    margin-top: 0.75rem;
  }

  .slide-buttons button {
    display: grid;
    grid-template-columns: 2.5rem minmax(0, 1fr);
    gap: 0.25rem 0.6rem;
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    color: var(--text);
    padding: 0.65rem;
    text-align: left;
    cursor: pointer;
  }

  .slide-buttons button.active {
    border-color: var(--accent);
  }

  .slide-buttons span {
    grid-row: span 2;
    color: var(--text-muted);
  }

  .slide-buttons strong,
  .slide-buttons small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .slide-buttons small {
    color: var(--text-muted);
  }

  .preview-head {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
    margin-bottom: 1rem;
  }

  .compare-grid {
    grid-template-columns: minmax(220px, 0.65fr) minmax(0, 1.35fr);
  }

  .source-preview {
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    padding: 1rem;
  }

  .source-preview p {
    margin-top: 0.75rem;
    color: var(--text-muted);
    line-height: 1.5;
  }

  .generated-select {
    margin-bottom: 0.75rem;
  }

  .generated-select label {
    display: grid;
    gap: 0.35rem;
    color: var(--text-muted);
    font-size: 0.78rem;
  }

  .generated-select select {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    color: var(--text);
    padding: 0.55rem 0.65rem;
  }

  .empty-render {
    display: grid;
    place-items: center;
    aspect-ratio: 16 / 9;
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text-muted);
    background: var(--surface-subtle);
  }

  .status,
  .redacted-list span {
    display: inline-flex;
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.22rem 0.5rem;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .status.failed {
    border-color: color-mix(in srgb, var(--danger) 45%, transparent);
    color: var(--danger);
  }

  .status.running {
    border-color: color-mix(in srgb, var(--accent) 45%, transparent);
    color: var(--accent);
  }

  .status.completed {
    border-color: color-mix(in srgb, var(--success) 45%, transparent);
    color: var(--success);
  }

  dl {
    display: grid;
    gap: 0.55rem;
    margin: 0 0 1rem;
  }

  dl div {
    border-top: 1px solid var(--border);
    padding-top: 0.5rem;
  }

  dt {
    color: var(--text-muted);
    font-size: 0.75rem;
  }

  dd {
    margin: 0.15rem 0 0;
    overflow-wrap: anywhere;
  }

  pre {
    margin: 0.5rem 0 1rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    padding: 0.75rem;
    max-height: 260px;
    overflow: auto;
    color: var(--text-muted);
    font-size: 0.75rem;
    line-height: 1.45;
  }

  .redaction-panel {
    grid-template-columns: minmax(0, 1fr) minmax(280px, 0.8fr);
    align-items: start;
  }

  .redacted-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  @media (max-width: 1180px) {
    .inspector-grid,
    .compare-grid,
    .redaction-panel {
      grid-template-columns: 1fr;
    }
  }
</style>
