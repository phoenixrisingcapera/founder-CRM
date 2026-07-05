<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const uploadDeckRoute = '/decks/new?firstBatch=slide_miniatures';
  const companyWebsiteRoute = '/decks/new?firstBatch=url_branding';
  const brandAssetsRoute = '/decks/new?firstBatch=logo_branding';
  const fallbackMessage =
    'We could not load your previous decks right now. You can still upload a new deck and continue testing.';

  const actionCards = [
    {
      step: '01',
      icon: '↥',
      variant: 'deck',
      title: 'Upload your deck',
      message:
        'Start with a PDF or PowerPoint deck. DeckAiStack will read the slides and prepare a workspace for AI review, edits, and improvements.',
      href: uploadDeckRoute,
      cta: 'Upload deck'
    },
    {
      step: '02',
      icon: '⌁',
      variant: 'website',
      title: 'Add company website',
      message:
        'Use the company website to give DeckAiStack extra context about the business, brand, product, and market positioning.',
      href: companyWebsiteRoute,
      cta: 'Add website'
    },
    {
      step: '03',
      icon: '◌',
      variant: 'brand',
      title: 'Add logo or brand assets',
      message:
        'Upload a logo or brand file so DeckAiStack can keep colours, visual style, and brand direction consistent.',
      href: brandAssetsRoute,
      cta: 'Upload brand assets'
    }
  ] as const;

  const previewRows = [
    {
      label: 'AI review',
      copy: 'Narrative, clarity, structure, and investor-readiness'
    },
    {
      label: 'Reviewable edits',
      copy: 'Suggestions stay editable before anything is applied'
    },
    {
      label: 'Export-ready versions',
      copy: 'Prepare versions for VC, board, IC, or advisory review'
    }
  ] as const;

  const workspaceName = $derived(data.workspace.workspace.name || 'Deck AIStack Workspace');
  const recentDecks = $derived(data.workspace.latestDecks ?? []);
  const workspaceNotice = $derived(
    data.workspaceLoadStatus?.status === 'degraded'
      ? data.workspaceLoadStatus.message ?? fallbackMessage
      : null
  );
</script>

<svelte:head>
  <title>Welcome | DeckAiStack</title>
</svelte:head>

<AppShell
  title="Welcome"
  subtitle="Upload a deck, review it with AI, and keep every suggestion reviewable before you apply it."
  activeNav="welcome"
  showTopBar={false}
  showFooterUtilities={true}
  deckLabel={workspaceName}
>
  <section class="welcome-page">
    <section class="hero panel">
      <div class="hero__copy">
        <div class="eyebrow">AI deck review workspace</div>
        <h1 class="display">Upload a deck.<br />Review it with AI.<br />Improve it faster.</h1>

        <p class="hero__subtitle">
          DeckAiStack helps you review investor decks, find weak points, improve the narrative, and prepare
          stronger versions for different audiences.
        </p>

        <div class="hero__actions">
          <a class="button hero__primary" href={uploadDeckRoute}>Upload your deck</a>
          <a class="button secondary hero__secondary" href={companyWebsiteRoute}>Add company website</a>
        </div>

        <p class="hero__trust">
          <span aria-hidden="true">🔒</span>
          Your files are private and secure. We never share your content.
        </p>

        {#if workspaceNotice}
          <div class="hero__notice" role="status">
            <strong>Previous decks unavailable</strong>
            <p>{workspaceNotice}</p>
          </div>
        {/if}
      </div>

      <aside class="hero__panel panel" aria-label="Workspace summary">
        <div class="hero__panel-eyebrow">Smart Deck workspace</div>
        <h2 class="hero__panel-title">Review your uploaded deck</h2>

        <div class="hero__panel-list">
          {#each previewRows as row}
            <div class="hero__panel-row">
              <span>{row.label}</span>
              <p>{row.copy}</p>
            </div>
          {/each}
        </div>

        <div class="hero__panel-chips" aria-label="Output types">
          <span class="pill">VC</span>
          <span class="pill">Board</span>
          <span class="pill">IC</span>
          <span class="pill">Advisory</span>
        </div>

        {#if recentDecks.length > 0}
          <div class="hero__history">
            <div class="hero__history-label">Recent decks</div>
            <ul>
              {#each recentDecks.slice(0, 3) as deck}
                <li>
                  <span>{deck.title}</span>
                  <small>{deck.status}</small>
                </li>
              {/each}
            </ul>
          </div>
        {/if}
      </aside>
    </section>

    <section class="content-grid" aria-label="Start here">
      <div class="action-stack">
        {#each actionCards as card}
          <article class="action-card panel">
            <div class="action-card__top">
              <span class="action-card__step">{card.step}</span>
              <div class="action-card__icon" aria-hidden="true">{card.icon}</div>
            </div>

            <div class="action-card__copy">
              <h2>{card.title}</h2>
              <p>{card.message}</p>
            </div>

            <div
              class="action-card__art"
              aria-hidden="true"
            >
              {#if card.variant === 'deck'}
                <div class="art-deck">
                  <span class="art-deck__sheet art-deck__sheet--back"></span>
                  <span class="art-deck__sheet art-deck__sheet--front">
                    <i></i>
                    <b></b>
                    <b></b>
                    <b></b>
                  </span>
                  <span class="art-deck__pdf">PDF</span>
                </div>
              {:else if card.variant === 'website'}
                <div class="art-website">
                  <span class="art-website__chrome"><i></i><i></i><i></i></span>
                  <span class="art-website__url">https://yourcompany.com</span>
                  <span class="art-website__panel art-website__panel--one"></span>
                  <span class="art-website__panel art-website__panel--two"></span>
                  <span class="art-website__panel art-website__panel--three"></span>
                </div>
              {:else}
                <div class="art-brand">
                  <span class="art-brand__mark">
                    <i></i>
                    <i></i>
                  </span>
                  <span class="art-brand__swatches">
                    <b></b>
                    <b></b>
                    <b></b>
                    <b></b>
                  </span>
                </div>
              {/if}
            </div>

            <a class="button action-card__button" href={card.href}>{card.cta}</a>
          </article>
        {/each}
      </div>

      <aside class="preview panel">
        <div class="preview__eyebrow">Investor-grade review flow</div>
        <h2 class="preview__title display">Smart Deck workspace, without the guesswork</h2>
        <p class="preview__lede">
          Upload first, then layer in company context and brand assets. Every suggestion stays reviewable before it
          becomes part of the deck.
        </p>

        <div class="preview__tracks">
          <div class="preview__track">
            <span class="preview__track-label">Upload</span>
            <strong>PDF or PowerPoint slides</strong>
          </div>
          <div class="preview__track">
            <span class="preview__track-label">Context</span>
            <strong>Website, brand, and positioning</strong>
          </div>
          <div class="preview__track">
            <span class="preview__track-label">Review</span>
            <strong>Editable AI suggestions and export-ready versions</strong>
          </div>
        </div>

        <div class="preview__footer">
          <span class="pill">Reviewable edits</span>
          <span class="pill">Private workspace</span>
        </div>
      </aside>
    </section>

    <div class="welcome-strip panel">
      <div class="welcome-strip__copy">
        <span class="welcome-strip__icon" aria-hidden="true">i</span>
        <div>
          <strong>New to DeckAiStack?</strong>
          <p>Upload a deck to see AI-powered insights, improvement suggestions, and export-ready versions.</p>
        </div>
      </div>

      <a class="welcome-strip__link" href={uploadDeckRoute}>
        Learn how it works
        <span aria-hidden="true">→</span>
      </a>
    </div>
  </section>
</AppShell>

<style>
  .welcome-page {
    display: grid;
    gap: 1rem;
    padding-bottom: 0.25rem;
  }

  .hero {
    position: relative;
    overflow: hidden;
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(18rem, 0.95fr);
    gap: 1.2rem;
    padding: clamp(1.25rem, 2vw, 1.75rem);
    border-color: color-mix(in srgb, var(--line-strong) 56%, var(--line));
    background:
      radial-gradient(circle at top left, color-mix(in srgb, var(--accent-soft) 72%, transparent), transparent 34rem),
      radial-gradient(circle at top right, color-mix(in srgb, var(--accent-2) 28%, transparent), transparent 28rem),
      linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 86%, transparent), color-mix(in srgb, var(--surface) 96%, transparent));
    box-shadow: var(--shadow-strong);
  }

  .hero__copy {
    min-width: 0;
    display: grid;
    gap: 1rem;
    align-content: start;
  }

  .display,
  h1,
  h2 {
    margin: 0;
    min-width: 0;
    overflow-wrap: anywhere;
    word-break: normal;
    line-height: 0.95;
    letter-spacing: -0.04em;
    font-style: normal;
  }

  h1.display {
    font-size: clamp(2.5rem, 5.1vw, 4.6rem);
    max-width: 12ch;
  }

  .hero__subtitle,
  .preview__lede {
    margin: 0;
    max-width: 58ch;
    color: var(--muted);
    line-height: 1.72;
    font-size: 1rem;
  }

  .hero__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: center;
  }

  .hero__primary {
    min-width: 13rem;
    padding-inline: 1.2rem;
    box-shadow: var(--shadow-glow-blue);
  }

  .hero__secondary {
    min-width: 13rem;
    padding-inline: 1.2rem;
  }

  .hero__trust {
    display: inline-flex;
    gap: 0.5rem;
    align-items: center;
    margin: 0;
    color: var(--ink-soft);
    font-size: 0.94rem;
    line-height: 1.5;
  }

  .hero__notice {
    display: grid;
    gap: 0.3rem;
    max-width: 48rem;
    padding: 0.95rem 1rem;
    border-radius: 16px;
    border: 1px solid color-mix(in srgb, var(--accent) 26%, var(--line));
    background:
      linear-gradient(180deg, color-mix(in srgb, var(--accent-soft) 42%, transparent), transparent),
      color-mix(in srgb, var(--surface-soft) 82%, transparent);
  }

  .hero__notice strong {
    color: var(--ink-strong);
    font-size: 0.95rem;
  }

  .hero__notice p {
    margin: 0;
    color: var(--muted);
    line-height: 1.55;
  }

  .hero__panel {
    display: grid;
    gap: 0.95rem;
    align-content: start;
    padding: 1.1rem;
    border-radius: calc(var(--radius-lg) - 4px);
    border-color: color-mix(in srgb, var(--line-strong) 42%, var(--line));
    background:
      radial-gradient(circle at top right, color-mix(in srgb, var(--accent) 16%, transparent), transparent 55%),
      linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 86%, transparent), color-mix(in srgb, var(--surface) 96%, transparent));
  }

  .hero__panel-eyebrow,
  .preview__eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.76rem;
    color: var(--accent);
  }

  .hero__panel-title,
  .preview__title {
    font-size: clamp(1.55rem, 2.7vw, 2.2rem);
    max-width: 12ch;
  }

  .hero__panel-list {
    display: grid;
    gap: 0.8rem;
  }

  .hero__panel-row {
    display: grid;
    gap: 0.25rem;
    padding: 0.9rem 0.95rem;
    border-radius: 18px;
    border: 1px solid var(--line);
    background: var(--surface-soft);
  }

  .hero__panel-row span,
  .preview__track-label,
  .hero__history-label {
    color: var(--ink-soft);
    font-size: 0.78rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .hero__panel-row p {
    margin: 0;
    color: var(--muted);
    line-height: 1.5;
  }

  .hero__panel-chips,
  .preview__footer {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
  }

  .hero__history {
    display: grid;
    gap: 0.55rem;
    padding-top: 0.2rem;
  }

  .hero__history ul {
    display: grid;
    gap: 0.5rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .hero__history li {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.82rem 0.9rem;
    border-radius: 14px;
    border: 1px solid var(--line);
    background: color-mix(in srgb, var(--surface-muted) 90%, transparent);
  }

  .hero__history span {
    min-width: 0;
    overflow-wrap: anywhere;
    color: var(--ink);
  }

  .hero__history small {
    color: var(--ink-soft);
    text-transform: capitalize;
    white-space: nowrap;
  }

  .content-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.2fr) minmax(18rem, 0.8fr);
    gap: 1rem;
    align-items: start;
  }

  .action-stack {
    display: grid;
    gap: 0.9rem;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    min-width: 0;
  }

  .action-card {
    min-width: 0;
    display: grid;
    gap: 1rem;
    padding: 1.15rem;
    border-color: color-mix(in srgb, var(--line-strong) 34%, var(--line));
    background:
      linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 74%, transparent), color-mix(in srgb, var(--surface) 94%, transparent));
    box-shadow: var(--shadow-card);
  }

  .action-card__top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
  }

  .action-card__step {
    display: inline-flex;
    align-items: center;
    min-height: 2rem;
    padding: 0 0.7rem;
    border-radius: 999px;
    border: 1px solid var(--line);
    color: var(--accent);
    background: var(--surface-chip);
    font-size: 0.74rem;
    letter-spacing: 0.12em;
    font-weight: 700;
  }

  .action-card__icon {
    width: 2.6rem;
    height: 2.6rem;
    display: grid;
    place-items: center;
    border-radius: 14px;
    color: var(--accent);
    border: 1px solid color-mix(in srgb, var(--accent) 24%, var(--line));
    background:
      radial-gradient(circle at top left, color-mix(in srgb, var(--accent-soft) 60%, transparent), transparent 65%),
      var(--surface-soft);
  }

  .action-card__copy {
    display: grid;
    gap: 0.45rem;
  }

  .action-card__copy h2 {
    font-size: 1.15rem;
    line-height: 1.15;
    max-width: 18ch;
  }

  .action-card__copy p {
    margin: 0;
    color: var(--muted);
    line-height: 1.65;
  }

  .action-card__art {
    position: relative;
    min-height: 11rem;
    border-radius: 20px;
    border: 1px solid var(--line);
    overflow: hidden;
    background:
      radial-gradient(circle at top left, color-mix(in srgb, var(--accent-soft) 65%, transparent), transparent 40%),
      linear-gradient(180deg, color-mix(in srgb, var(--surface-soft) 86%, transparent), color-mix(in srgb, var(--surface-muted) 90%, transparent));
  }

  .art-deck,
  .art-website,
  .art-brand {
    position: absolute;
    inset: 0;
  }

  .art-deck {
    display: grid;
    place-items: center;
  }

  .art-deck__sheet {
    position: absolute;
    width: 52%;
    aspect-ratio: 0.72;
    border-radius: 18px;
    border: 1px solid color-mix(in srgb, var(--accent) 18%, var(--line));
    background: linear-gradient(180deg, rgba(16, 28, 64, 0.96), rgba(8, 14, 33, 0.98));
    box-shadow: 0 22px 44px rgba(3, 9, 28, 0.3);
  }

  .art-deck__sheet--back {
    transform: translateX(1.8rem) translateY(-0.65rem) rotate(6deg);
    background: linear-gradient(180deg, rgba(24, 39, 83, 0.96), rgba(7, 14, 31, 0.98));
    opacity: 0.78;
  }

  .art-deck__sheet--front {
    transform: translateX(-0.6rem) translateY(0.45rem) rotate(-4deg);
    display: grid;
    align-content: start;
    gap: 0.35rem;
    padding: 0.9rem 0.85rem;
  }

  .art-deck__sheet--front i,
  .art-deck__sheet--front b {
    display: block;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(113, 183, 255, 0.92), rgba(124, 58, 237, 0.42));
  }

  .art-deck__sheet--front i {
    width: 44%;
    height: 0.34rem;
  }

  .art-deck__sheet--front b {
    height: 0.7rem;
  }

  .art-deck__sheet--front b:nth-of-type(2) {
    width: 82%;
  }

  .art-deck__sheet--front b:nth-of-type(3) {
    width: 66%;
  }

  .art-deck__sheet--front b:nth-of-type(4) {
    width: 90%;
  }

  .art-deck__pdf {
    position: absolute;
    right: 1rem;
    bottom: 0.9rem;
    width: 2rem;
    height: 2.6rem;
    display: grid;
    place-items: center;
    border-radius: 0.55rem;
    color: #ff4762;
    background: linear-gradient(180deg, #ffffff, #f3f6ff);
    box-shadow: 0 10px 24px rgba(3, 9, 28, 0.22);
  }

  .art-website {
    padding: 1rem;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto 1fr;
    gap: 0.6rem;
    align-content: start;
  }

  .art-website__chrome {
    grid-column: 1 / -1;
    display: flex;
    gap: 0.35rem;
  }

  .art-website__chrome i {
    width: 0.55rem;
    height: 0.55rem;
    border-radius: 999px;
    background: var(--line-strong);
  }

  .art-website__url {
    grid-column: 1 / -1;
    padding: 0.55rem 0.7rem;
    border-radius: 0.8rem;
    border: 1px solid color-mix(in srgb, var(--line-strong) 48%, var(--line));
    color: var(--ink-soft);
    font-size: 0.78rem;
    background: var(--surface-soft);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .art-website__panel {
    border-radius: 16px;
    border: 1px solid var(--line);
    background: linear-gradient(180deg, rgba(16, 29, 66, 0.94), rgba(8, 15, 34, 0.98));
  }

  .art-website__panel--one {
    grid-column: 1 / -1;
    min-height: 2.7rem;
  }

  .art-website__panel--two,
  .art-website__panel--three {
    min-height: 4rem;
  }

  .art-brand {
    display: grid;
    place-items: center;
    gap: 0.95rem;
    padding: 1rem;
  }

  .art-brand__mark {
    position: relative;
    width: min(62%, 8rem);
    aspect-ratio: 1;
    display: grid;
    place-items: center;
    border-radius: 1.6rem;
    border: 1px dashed color-mix(in srgb, var(--line-strong) 46%, var(--line));
    background:
      radial-gradient(circle at 30% 25%, color-mix(in srgb, var(--accent) 26%, transparent), transparent 35%),
      linear-gradient(180deg, rgba(18, 30, 71, 0.95), rgba(8, 14, 31, 0.98));
  }

  .art-brand__mark i {
    position: absolute;
    width: 2.8rem;
    height: 1.8rem;
    clip-path: polygon(0 100%, 45% 0, 70% 55%, 100% 0, 100% 100%);
    background: linear-gradient(135deg, #78a9ff, #654dff);
  }

  .art-brand__mark i:last-child {
    transform: translateX(0.65rem) translateY(0.35rem) scale(0.72);
    background: linear-gradient(135deg, #65ffd5, #4eb9ff);
  }

  .art-brand__swatches {
    display: flex;
    gap: 0.45rem;
    align-items: center;
  }

  .art-brand__swatches b {
    width: 1.2rem;
    height: 1.2rem;
    border-radius: 0.35rem;
    box-shadow: 0 10px 20px rgba(3, 9, 28, 0.22);
  }

  .art-brand__swatches b:nth-child(1) {
    background: #6a66ff;
  }

  .art-brand__swatches b:nth-child(2) {
    background: #8f4dff;
  }

  .art-brand__swatches b:nth-child(3) {
    background: #58d6ff;
  }

  .art-brand__swatches b:nth-child(4) {
    background: #f3f7ff;
  }

  .action-card__button {
    width: 100%;
    min-height: 3rem;
    white-space: nowrap;
  }

  .preview {
    min-width: 0;
    display: grid;
    gap: 0.95rem;
    padding: 1.2rem;
    border-color: color-mix(in srgb, var(--line-strong) 38%, var(--line));
    background:
      radial-gradient(circle at top, color-mix(in srgb, var(--accent) 14%, transparent), transparent 42%),
      linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 78%, transparent), color-mix(in srgb, var(--surface) 96%, transparent));
    box-shadow: var(--shadow-strong);
  }

  .preview__title {
    max-width: 11ch;
  }

  .preview__lede {
    font-size: 0.98rem;
  }

  .preview__tracks {
    display: grid;
    gap: 0.75rem;
  }

  .preview__track {
    display: grid;
    gap: 0.25rem;
    padding: 0.95rem;
    border-radius: 16px;
    border: 1px solid var(--line);
    background: var(--surface-soft);
  }

  .preview__track strong {
    color: var(--ink-strong);
    line-height: 1.45;
  }

  .preview__footer {
    padding-top: 0.1rem;
  }

  .welcome-strip {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    padding: 1rem 1.1rem;
    border-color: color-mix(in srgb, var(--line-strong) 28%, var(--line));
    background:
      linear-gradient(180deg, color-mix(in srgb, var(--surface-strong) 76%, transparent), color-mix(in srgb, var(--surface) 94%, transparent));
  }

  .welcome-strip__copy {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    min-width: 0;
  }

  .welcome-strip__icon {
    width: 2rem;
    height: 2rem;
    display: grid;
    place-items: center;
    border-radius: 999px;
    color: var(--accent);
    border: 1px solid color-mix(in srgb, var(--accent) 30%, var(--line));
    background: var(--surface-chip);
  }

  .welcome-strip__copy strong {
    display: block;
    margin-bottom: 0.15rem;
    color: var(--ink-strong);
  }

  .welcome-strip__copy p {
    margin: 0;
    color: var(--muted);
    line-height: 1.5;
  }

  .welcome-strip__link {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--accent);
    white-space: nowrap;
  }

  .pill {
    white-space: nowrap;
  }

  @media (max-width: 1120px) {
    .hero,
    .content-grid {
      grid-template-columns: 1fr;
    }

    .action-stack {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .hero__panel-title,
    .preview__title {
      max-width: none;
    }

    .welcome-strip {
      align-items: flex-start;
      flex-direction: column;
    }
  }

  @media (max-width: 760px) {
    .hero,
    .preview,
    .hero__panel,
    .action-card {
      padding: 1rem;
    }

    .hero__actions {
      flex-direction: column;
      align-items: stretch;
    }

    .hero__primary,
    .hero__secondary,
    .action-card__button {
      width: 100%;
      min-width: 0;
    }

    .action-stack {
      grid-template-columns: 1fr;
    }

    h1.display {
      max-width: none;
    }

    .hero__history li {
      align-items: flex-start;
      flex-direction: column;
      gap: 0.25rem;
    }

    .action-card__art {
      min-height: 9.5rem;
    }

    .art-deck__sheet {
      width: 58%;
    }
  }
</style>
