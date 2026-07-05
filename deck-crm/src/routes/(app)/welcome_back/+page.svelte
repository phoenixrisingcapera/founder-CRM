<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { DeckGraph, DeckShellProperties } from '@deck-aistack-codes/shared';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  function primaryDeck() {
    const activeId = data.workspace.activeDeckId;
    return data.decks.find((deck) => deck.id === activeId) ?? data.decks[0] ?? null;
  }

  function primaryDeckGraph(): DeckGraph | null {
    return data.primaryDeckGraph ?? null;
  }

  function primaryDeckProperties(): DeckShellProperties | null {
    return data.primaryDeckProperties ?? null;
  }

  function latestBatchId() {
    return data.latestBatches[0]?.id ?? null;
  }

  function lastSlideId() {
    const graph = primaryDeckGraph();
    return graph?.slides.at(-1)?.id ?? graph?.slides[0]?.id ?? null;
  }

  function deckSlideCount() {
    return primaryDeckGraph()?.slides.length ?? 0;
  }

  function formatDate(value: string | undefined | null) {
    if (!value) return 'Recently updated';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Recently updated';
    return date.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  }

  function statusLabel(status: string) {
    return status.replaceAll('_', ' ');
  }

  function continueEditingHref(deckId: string) {
    const slideId = lastSlideId();
    const batchId = latestBatchId();
    const params = new URLSearchParams();
    if (slideId) params.set('slide', slideId);
    if (batchId) params.set('batchId', batchId);
    const query = params.toString();
    return `/decks/${deckId}/smart-deck${query ? `?${query}` : ''}`;
  }

  function slideMapHref(deckId: string) {
    return `/decks/${deckId}/smart-deck`;
  }

  const brandSwatches = [
    { label: 'Primary', className: 'swatch swatch--primary', value: 'Workspace primary' },
    { label: 'Secondary', className: 'swatch swatch--secondary', value: 'Workspace secondary' },
    { label: 'Accent', className: 'swatch swatch--accent', value: 'Workspace accent' },
    { label: 'Canvas', className: 'swatch swatch--canvas', value: 'Deck canvas' },
    { label: 'Text', className: 'swatch swatch--text', value: 'Reading layer' }
  ];

  function deckAccentClass(index: number) {
    return `deck-mini__preview-bar deck-mini__preview-bar--${(index % 3) + 1}`;
  }

  function brandMemory() {
    const deck = primaryDeck();
    const properties = primaryDeckProperties();

    return {
      id: deck?.id ?? properties?.deckId ?? 'brand_memory',
      companyName: properties?.companyName ?? deck?.title ?? 'Main deck',
      visualDirection: properties?.visualDirection ?? 'Investor-grade direction retained from the latest working deck.'
    };
  }

  function previewTitle(deckTitle: string) {
    const parts = deckTitle.split(' ');
    return parts.slice(0, 2).join(' ');
  }

  function previewSlides() {
    const slides = primaryDeckGraph()?.slides ?? [];
    return slides.slice(0, 3).map((slide) => {
      const lines = slide.rawText
        .split('\n')
        .map((line) => line.replace(/^•\s*/, '').trim())
        .filter(Boolean);

      return {
        id: slide.id,
        title: slide.title,
        body: lines[0] ?? slide.narrativeNotes ?? 'Investor-grade slide preview.',
        bullets: lines.slice(1, 4),
        role: slide.role
      };
    });
  }

  function heroPreviewSlide() {
    return previewSlides()[0] ?? null;
  }

  function deckSourceFileName() {
    return primaryDeckGraph()?.deck.file?.filename ?? primaryDeckProperties()?.sourceFileName ?? 'Sample deck file';
  }

  function compactSourceName() {
    const fileName = deckSourceFileName();
    return fileName.length > 26 ? `${fileName.slice(0, 23)}...` : fileName;
  }

  function deckPositionLabel(index: number) {
    return index === 0 ? 'Active deck' : `Saved deck ${index + 1}`;
  }

  function workspaceNotice() {
    if (data.workspaceLoadStatus?.status !== 'degraded') return null;
    return {
      title: 'Workspace connection needs attention',
      message:
        'You can continue from this page. Some saved workspace details are temporarily unavailable, so open an existing deck or upload a new one.',
      detail: data.workspaceLoadStatus.message
    };
  }

</script>

<AppShell
  title="Welcome back"
  subtitle="Resume saved deck work with brand memory and provider status ready."
  activeNav="welcome-back"
  showTopBarCopy={false}
  compactTopBar={true}
  showTopBarSearch={false}
  deckLabel={data.workspace.workspace.name}
  currentDeckId={data.workspace.activeDeckId}
  latestBatches={data.latestBatches}
>
  <section class="welcome-screen">
    <section class="welcome-hero panel">
      <div class="welcome-hero__copy">
        <div class="eyebrow">Welcome back</div>
        <h2>Resume the last Deck AIStack workspace without restarting intake.</h2>
        <p class="welcome-hero__lede">
          Your saved deck, brand direction, and workspace provider are ready to continue from the latest working state.
        </p>

        <div class="welcome-hero__actions">
          {#if primaryDeck()}
            <a class="button welcome-hero__primary" href={continueEditingHref(primaryDeck()!.id)}>Continue editing</a>
            <a class="button secondary welcome-hero__secondary" href={slideMapHref(primaryDeck()!.id)}>Open slide map</a>
          {:else}
            <a class="button welcome-hero__primary" href="/decks/new">Upload your first deck</a>
          {/if}
        </div>

        {#if workspaceNotice()}
          <div class="welcome-runtime-notice" role="status">
            <strong>{workspaceNotice()?.title}</strong>
            <p>{workspaceNotice()?.message}</p>
            {#if workspaceNotice()?.detail}
              <span>{workspaceNotice()?.detail}</span>
            {/if}
          </div>
        {/if}

        <div class="welcome-hero__signals">
          <span class="pill">{data.workspace.deckCount} deck{data.workspace.deckCount === 1 ? '' : 's'} saved</span>
          <span class="pill">Built-in AI ready</span>
          <span class="pill">Persistent workspace memory</span>
        </div>
      </div>

      <div class="welcome-hero__visual" aria-hidden="true">
        <div class="welcome-hero__glow welcome-hero__glow--top"></div>
        <div class="welcome-hero__glow welcome-hero__glow--bottom"></div>

        <div class="hero-stack">
          <div class="hero-stack__card hero-stack__card--back"></div>
          <div class="hero-stack__card hero-stack__card--mid"></div>

          <section class="hero-stack__card hero-stack__card--front">
            <header class="hero-stack__header">
              <span class="hero-stack__kicker">Returning workspace</span>
              <span class="hero-stack__status">{primaryDeck() ? statusLabel(primaryDeck()!.status) : 'ready'}</span>
            </header>

            <div class="hero-stack__brand">
              <div class="hero-stack__brand-mark">DD</div>
              <div>
                <strong>{primaryDeck()?.title ?? 'Deck AIStack workspace'}</strong>
                <p>{brandMemory().visualDirection}</p>
              </div>
            </div>

            <div class="hero-stack__canvas">
              <div class="hero-slide">
                <div class="hero-slide__header">
                  <span class="hero-slide__eyebrow">{heroPreviewSlide()?.role ?? 'Deck preview'}</span>
                  <span>{deckSlideCount() || '18'} slides</span>
                </div>
                <strong>{heroPreviewSlide()?.title ?? previewTitle(primaryDeck()?.title ?? 'Sample deck preview')}</strong>
                <p>{heroPreviewSlide()?.body ?? 'Investor-ready memory retained from the latest working deck.'}</p>

                <div class="hero-slide__content">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>

              <aside class="hero-stack__panel">
                <div class="hero-review-row">
                  <span>Memory</span>
                  <strong>Loaded</strong>
                </div>
                <div class="hero-review-row">
                  <span>AI</span>
                  <strong>Ready</strong>
                </div>
                <div class="hero-progress" aria-hidden="true">
                  <span></span>
                </div>
              </aside>
            </div>

            <footer class="hero-stack__footer">
              <div class="hero-mini-card">
                <span class="hero-mini-card__label">Source file</span>
                <strong>{compactSourceName()}</strong>
              </div>
              <div class="hero-mini-card">
                <span class="hero-mini-card__label">Latest version</span>
                <strong>{latestBatchId() ? 'Iteration ready' : 'No iteration yet'}</strong>
              </div>
            </footer>
          </section>
        </div>
      </div>
    </section>

    <section class="welcome-back-grid">
      <article class="panel resume-card resume-card--primary">
        <div class="resume-card__header">
          <div>
            <div class="eyebrow">{data.workspace.deckCount > 1 ? 'Deck library' : 'Last deck card'}</div>
            <h3>{data.workspace.deckCount > 1 ? 'Choose a deck to continue' : primaryDeck()?.title ?? 'No saved deck yet'}</h3>
            <p class="muted">
              {data.workspace.deckCount > 1
                ? 'Reopen the right workspace and continue from the last saved deck state.'
                : 'Your last deck is ready with saved slides, source context, and continuation actions.'}
            </p>
          </div>
          <span class="resume-card__badge">{data.workspace.deckCount} saved</span>
        </div>

        {#if data.workspace.deckCount > 1}
          <div class="deck-library-grid">
            {#each data.decks as deck, index}
              <article class="deck-mini">
                <div class="deck-mini__preview">
                  <div class={deckAccentClass(index)}></div>
                  <div class="deck-mini__preview-copy">
                    <strong>{previewTitle(deck.title)}</strong>
                    <span>{statusLabel(deck.status)}</span>
                  </div>
                </div>

                <div class="deck-mini__body">
                  <div>
                    <strong>{deck.title}</strong>
                    <p class="muted">Last edited {formatDate(deck.updatedAt)}</p>
                  </div>

                  <dl class="deck-mini__meta">
                    <div><dt>Position</dt><dd>{deckPositionLabel(index)}</dd></div>
                    <div><dt>Status</dt><dd>{statusLabel(deck.status)}</dd></div>
                  </dl>

                  <div class="deck-mini__swatches">
                    {#each brandSwatches.slice(0, 4) as swatch}
                      <span class={swatch.className} title={swatch.label}></span>
                    {/each}
                  </div>

                  <a class="button secondary" href={`/decks/${deck.id}/smart-deck`}>Open deck</a>
                </div>
              </article>
            {/each}
          </div>
        {:else if primaryDeck()}
          <div class="last-deck-card">
            <div class="last-deck-card__preview">
              <div class="last-deck-card__thumbnail">
                {#each previewSlides() as slide, index}
                  <article class={`thumbnail-slide thumbnail-slide--${index + 1}`}>
                    <span class="thumbnail-slide__role">{slide.role}</span>
                    <strong>{slide.title}</strong>
                    <p>{slide.body}</p>
                  </article>
                {/each}
                <div class="last-deck-card__thumbnail-footer">
                  {#each brandSwatches.slice(0, 3) as swatch}
                    <i class={swatch.className} title={swatch.label}></i>
                  {/each}
                </div>
              </div>
            </div>

            <div class="last-deck-card__body">
              <div class="last-deck-card__title">
                <h4>{primaryDeck()!.title}</h4>
                <p class="muted">Last edited {formatDate(primaryDeck()!.updatedAt)}</p>
              </div>

              <dl class="state-grid">
                <div><dt>Source file</dt><dd>{compactSourceName()}</dd></div>
                <div><dt>Last slide</dt><dd>{lastSlideId() ? 'Saved' : 'Unavailable'}</dd></div>
                <div><dt>Latest version</dt><dd>{latestBatchId() ? 'Iteration ready' : 'No iteration yet'}</dd></div>
                <div><dt>Status</dt><dd>{statusLabel(primaryDeck()!.status)}</dd></div>
              </dl>

              <div class="last-deck-card__actions">
                <a class="button" href={continueEditingHref(primaryDeck()!.id)}>Continue editing</a>
                <a class="button secondary" href={slideMapHref(primaryDeck()!.id)}>Open slide map</a>
              </div>
            </div>
          </div>
        {:else}
          <div class="empty-state-card">
            <p class="muted">No saved deck was found for this workspace yet.</p>
            <a class="button" href="/decks/new">Upload first deck</a>
          </div>
        {/if}
      </article>

      <article class="panel resume-card">
        <div class="eyebrow">Guided deck intake</div>
        <h3>Brand memory from your main deck</h3>
        <p class="muted">Saved brand direction carries into new versions, guided intake, and export preparation.</p>

        <div class="brand-memory__swatches">
          {#each brandSwatches as swatch}
            <div><span class={swatch.className}></span><strong>{swatch.label}</strong><small>{swatch.value}</small></div>
          {/each}
        </div>

        <div class="resume-card__footer-note">
          <strong>{brandMemory().companyName}</strong>
          <span>{brandMemory().visualDirection}</span>
        </div>
      </article>
    </section>
  </section>
</AppShell>

<style>
  .welcome-screen {
    display: grid;
    gap: 1rem;
    min-height: 0;
    overflow: visible;
  }

  .welcome-hero,
  .resume-card {
    position: relative;
    overflow: hidden;
    border-color: color-mix(in srgb, var(--line-strong) 68%, transparent);
    background:
      radial-gradient(circle at top right, color-mix(in srgb, var(--accent-2) 18%, transparent), transparent 24rem),
      radial-gradient(circle at bottom left, color-mix(in srgb, var(--accent) 14%, transparent), transparent 22rem),
      linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 88%, transparent), color-mix(in srgb, var(--bg) 96%, transparent));
  }

  .welcome-hero {
    padding: 1.7rem;
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.95fr);
    gap: 1.2rem;
    align-items: center;
  }

  .welcome-hero__copy {
    display: grid;
    gap: 0.95rem;
    max-width: 44rem;
  }

  .welcome-hero__lede {
    margin: 0;
    color: var(--muted);
    line-height: 1.7;
    max-width: 42rem;
  }

  .welcome-hero__actions,
  .welcome-hero__signals,
  .last-deck-card__actions {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .welcome-runtime-notice {
    display: grid;
    gap: 0.35rem;
    max-width: 42rem;
    padding: 0.9rem 1rem;
    border: 1px solid color-mix(in srgb, var(--warn) 42%, var(--line));
    border-radius: 14px;
    background:
      linear-gradient(180deg, color-mix(in srgb, var(--warn) 12%, transparent), rgba(255, 255, 255, 0.03));
  }

  .welcome-runtime-notice strong {
    color: var(--ink);
    font-size: 0.95rem;
  }

  .welcome-runtime-notice p,
  .welcome-runtime-notice span {
    margin: 0;
    color: var(--ink-soft);
    line-height: 1.5;
    font-size: 0.9rem;
  }

  .welcome-runtime-notice span {
    color: var(--muted);
    overflow-wrap: anywhere;
  }

  .welcome-hero__visual {
    min-height: 400px;
    position: relative;
    display: grid;
    place-items: center;
  }

  .welcome-hero__glow {
    position: absolute;
    border-radius: 999px;
    filter: blur(46px);
    opacity: 0.46;
  }

  .welcome-hero__glow--top {
    width: 240px;
    height: 240px;
    top: 0;
    right: 3rem;
    background: radial-gradient(circle, color-mix(in srgb, var(--accent-2) 34%, transparent), transparent 70%);
  }

  .welcome-hero__glow--bottom {
    width: 220px;
    height: 220px;
    bottom: 0;
    left: 2rem;
    background: radial-gradient(circle, color-mix(in srgb, var(--accent) 24%, transparent), transparent 70%);
  }

  .hero-stack {
    position: relative;
    width: min(100%, 31rem);
    min-height: 350px;
  }

  .hero-stack__card {
    position: absolute;
    inset: 0;
    border-radius: 24px;
    border: 1px solid color-mix(in srgb, var(--line-strong) 75%, transparent);
  }

  .hero-stack__card--back {
    transform: translate(16px, 18px);
    background: linear-gradient(140deg, color-mix(in srgb, var(--accent) 18%, var(--surface-soft)), var(--surface-muted));
  }

  .hero-stack__card--mid {
    transform: translate(8px, 9px);
    background: linear-gradient(140deg, color-mix(in srgb, var(--accent-2) 16%, var(--surface-soft)), var(--surface-muted));
  }

  .hero-stack__card--front {
    padding: 1.15rem;
    display: grid;
    gap: 0.95rem;
    background:
      linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 94%, transparent), color-mix(in srgb, var(--bg) 96%, transparent)),
      var(--surface);
    box-shadow: var(--shadow-strong);
  }

  .hero-stack__header,
  .hero-stack__brand,
  .hero-stack__canvas,
  .hero-stack__footer {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
  }

  .hero-stack__header {
    align-items: center;
  }

  .hero-stack__kicker,
  .hero-stack__status,
  .hero-mini-card__label {
    font-size: 0.76rem;
    color: var(--ink-soft);
  }

  .hero-stack__status {
    padding: 0.35rem 0.65rem;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: var(--surface-soft);
  }

  .hero-stack__brand {
    align-items: center;
  }

  .hero-stack__brand p,
  .hero-mini-card__label {
    margin: 0.2rem 0 0;
    color: var(--muted);
  }

  .hero-stack__brand-mark {
    width: 52px;
    height: 52px;
    border-radius: 16px;
    display: grid;
    place-items: center;
    font-weight: 700;
    background: var(--gradient-brand);
    color: var(--button-primary-ink);
  }

  .hero-stack__canvas {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 9.5rem;
    align-items: stretch;
  }

  .hero-slide,
  .hero-stack__panel,
  .hero-mini-card {
    border: 1px solid var(--line);
    border-radius: 18px;
    background: var(--surface-soft);
    padding: 1rem;
  }

  .hero-stack__panel {
    display: grid;
    gap: 0.7rem;
    align-content: start;
  }

  .hero-slide {
    display: grid;
    gap: 0.7rem;
    min-width: 0;
    background:
      radial-gradient(circle at 85% 20%, color-mix(in srgb, var(--accent) 14%, transparent), transparent 35%),
      linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 84%, transparent), color-mix(in srgb, var(--bg) 88%, transparent));
  }

  .hero-slide__header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    color: var(--muted);
    font-size: 0.74rem;
    min-width: 0;
  }

  .hero-slide__eyebrow {
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
  }

  .hero-slide strong {
    font-size: 1.16rem;
    letter-spacing: -0.03em;
    color: var(--ink-strong);
  }

  .hero-slide p {
    margin: 0;
    color: var(--muted);
    line-height: 1.5;
  }

  .hero-slide__content {
    display: grid;
    gap: 0.45rem;
    margin-top: 0.15rem;
  }

  .hero-slide__content span {
    height: 0.44rem;
    border-radius: 999px;
    background: linear-gradient(90deg, color-mix(in srgb, var(--accent) 64%, transparent), color-mix(in srgb, var(--accent) 8%, transparent));
  }

  .hero-slide__content span:nth-child(2) {
    width: 82%;
  }

  .hero-slide__content span:nth-child(3) {
    width: 58%;
  }

  .hero-review-row {
    display: grid;
    gap: 0.24rem;
    padding-bottom: 0.7rem;
    border-bottom: 1px solid var(--line);
  }

  .hero-review-row span {
    color: var(--muted);
    font-size: 0.76rem;
  }

  .hero-review-row strong {
    color: var(--ink-strong);
    font-size: 0.94rem;
    overflow-wrap: anywhere;
  }

  .hero-progress {
    height: 0.42rem;
    border-radius: 999px;
    background: var(--surface-muted);
    overflow: hidden;
    margin-top: 0.2rem;
  }

  .hero-progress span {
    display: block;
    width: 74%;
    height: 100%;
    border-radius: inherit;
    background: var(--gradient-brand);
  }

  .hero-mini-card {
    flex: 1;
    min-width: 0;
    padding: 0.78rem 0.85rem;
  }

  .hero-mini-card strong,
  .resume-card h3,
  .last-deck-card__title h4 {
    margin: 0;
    letter-spacing: -0.03em;
  }

  .hero-mini-card strong {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.9rem;
  }

  .welcome-back-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.8fr) minmax(280px, 0.8fr);
    gap: 1rem;
    align-items: start;
  }

  .resume-card {
    padding: 1.35rem;
    display: grid;
    gap: 1rem;
    min-height: 100%;
  }

  .resume-card--primary {
    min-width: 0;
  }

  .resume-card__header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    align-items: start;
  }

  .resume-card__badge {
    padding: 0.42rem 0.75rem;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: var(--surface-soft);
    color: var(--ink-soft);
    font-size: 0.78rem;
  }

  .last-deck-card {
    display: grid;
    grid-template-columns: minmax(220px, 0.78fr) minmax(0, 1fr);
    gap: 1rem;
    align-items: stretch;
  }

  .last-deck-card__preview,
  .deck-mini__preview {
    border-radius: 22px;
    border: 1px solid var(--line);
    background: linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 90%, transparent), color-mix(in srgb, var(--bg) 88%, transparent));
    padding: 1rem;
  }

  .last-deck-card__thumbnail {
    height: 100%;
    min-height: 220px;
    border-radius: 18px;
    border: 1px solid color-mix(in srgb, var(--line-strong) 72%, transparent);
    background: linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 88%, transparent), color-mix(in srgb, var(--bg) 94%, transparent));
    display: grid;
    gap: 0.9rem;
    padding: 1rem;
  }

  .thumbnail-slide {
    display: grid;
    gap: 0.35rem;
    padding: 0.9rem 1rem;
    border-radius: 16px;
    border: 1px solid color-mix(in srgb, var(--line-strong) 68%, transparent);
    background: linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 90%, transparent), color-mix(in srgb, var(--surface) 96%, transparent));
    box-shadow: var(--shadow-soft);
  }

  .thumbnail-slide--1 {
    transform: rotate(-1.5deg);
  }

  .thumbnail-slide--2 {
    transform: translateX(1.1rem) rotate(1.4deg);
  }

  .thumbnail-slide--3 {
    transform: translateX(2.2rem) rotate(-0.8deg);
  }

  .thumbnail-slide__role {
    font-size: 0.68rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
  }

  .thumbnail-slide strong {
    font-size: 0.95rem;
    letter-spacing: -0.02em;
  }

  .thumbnail-slide p {
    margin: 0;
    color: var(--muted);
    line-height: 1.45;
    font-size: 0.78rem;
  }

  .last-deck-card__thumbnail-footer {
    margin-top: auto;
    display: flex;
    gap: 0.55rem;
  }

  .last-deck-card__thumbnail-footer i,
  .deck-mini__swatches span,
  .brand-memory__swatches span {
    display: inline-block;
    border-radius: 12px;
    border: 1px solid var(--line-contrast);
  }

  .swatch--primary {
    background: var(--color-primary);
  }

  .swatch--secondary {
    background: var(--color-secondary);
  }

  .swatch--accent {
    background: var(--color-accent);
  }

  .swatch--canvas {
    background: linear-gradient(135deg, var(--surface-strong), var(--surface-soft));
  }

  .swatch--text {
    background: linear-gradient(135deg, var(--ink-strong), var(--muted));
  }

  .last-deck-card__thumbnail-footer i {
    width: 28px;
    height: 28px;
  }

  .last-deck-card__body {
    display: grid;
    gap: 1rem;
    align-content: start;
  }

  .state-grid,
  .deck-mini__meta {
    margin: 0;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.8rem;
  }

  .state-grid div,
  .deck-mini__meta div,
  .resume-card__footer-note {
    border-radius: 18px;
  }

  .state-grid div,
  .deck-mini__meta div,
  .resume-card__footer-note {
    border: 1px solid var(--line);
    background: var(--surface-soft);
    padding: 0.9rem 1rem;
  }

  dt {
    color: var(--muted);
    font-size: 0.76rem;
    text-transform: lowercase;
    letter-spacing: 0.04em;
  }

  dd {
    margin: 0.3rem 0 0;
    color: var(--ink-strong);
    font-weight: 600;
    word-break: break-word;
  }

  .deck-library-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
  }

  .deck-mini {
    display: grid;
    gap: 0.9rem;
  }

  .deck-mini__preview {
    min-height: 150px;
    display: grid;
    align-content: space-between;
  }

  .deck-mini__preview-bar {
    height: 18px;
    width: 45%;
    border-radius: 999px;
    background: var(--gradient-brand);
  }

  .deck-mini__preview-bar--2 {
    background: linear-gradient(90deg, var(--color-accent), var(--color-primary));
  }

  .deck-mini__preview-bar--3 {
    background: linear-gradient(90deg, var(--color-secondary), var(--color-accent));
  }

  .deck-mini__preview-copy {
    display: grid;
    gap: 0.25rem;
  }

  .deck-mini__preview-copy span {
    color: var(--muted);
    font-size: 0.82rem;
  }

  .deck-mini__body {
    display: grid;
    gap: 0.9rem;
  }

  .deck-mini__swatches {
    display: flex;
    gap: 0.45rem;
  }

  .deck-mini__swatches span {
    width: 22px;
    height: 22px;
  }

  .empty-state-card {
    display: grid;
    gap: 1rem;
    justify-items: start;
  }

  .brand-memory__swatches {
    display: grid;
    gap: 0.8rem;
    min-width: 0;
  }

  .brand-memory__swatches div {
    display: grid;
    grid-template-columns: 40px minmax(0, 1fr);
    column-gap: 0.8rem;
    row-gap: 0.15rem;
    align-items: center;
    min-width: 0;
  }

  .brand-memory__swatches span {
    grid-row: span 3;
    width: 40px;
    height: 40px;
  }

  .brand-memory__swatches strong {
    display: block;
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .brand-memory__swatches small,
  .resume-card__footer-note span {
    color: var(--muted);
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .resume-card__footer-note {
    display: grid;
    gap: 0.35rem;
  }

  .status-dot {
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 999px;
    background: var(--warn);
    box-shadow: 0 0 0 6px color-mix(in srgb, var(--warn) 18%, transparent);
  }

  .status-dot.active {
    background: var(--success);
    box-shadow: 0 0 0 6px color-mix(in srgb, var(--success) 18%, transparent);
  }

  h2,
  h3,
  h4 {
    margin: 0;
  }

  @media (max-width: 1220px) {
    .welcome-hero,
    .welcome-back-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 880px) {
    .last-deck-card,
    .state-grid,
    .deck-mini__meta {
      grid-template-columns: 1fr;
    }

    .brand-memory__swatches {
      grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
    }
  }

  @media (max-width: 720px) {
    .welcome-hero,
    .resume-card {
      padding: 1.15rem;
    }

    .welcome-hero__actions .button,
    .last-deck-card__actions .button {
      width: 100%;
      justify-content: center;
    }

    .brand-memory__swatches {
      grid-template-columns: minmax(0, 1fr);
    }

    .welcome-hero__visual {
      min-height: 340px;
    }
  }
</style>
