<script lang="ts">
  import { goto } from '$app/navigation';
  import type { WorkspaceAiProviderRouteResponse, WorkspaceSummary } from '@deck-aistack-codes/shared';
  import FirstDeckWorkflow from '$components/FirstDeckWorkflow.svelte';
  import UploadFirstDeckCard from '$components/UploadFirstDeckCard.svelte';

  interface Props {
    workspace: WorkspaceSummary;
    aiProviderSummary: WorkspaceAiProviderRouteResponse['summary'];
    title?: string;
    subtitle?: string;
  }

  let {
    workspace,
    aiProviderSummary,
    title = 'Welcome to Deck AIStack',
    subtitle = 'Your private AI deck workspace is ready. Start with one source deck, then review every suggestion before anything changes.'
  }: Props = $props();

  const nextSteps = [
    {
      title: 'Upload your existing deck',
      detail: 'Start from the real source file so Deck AIStack can preserve the original deck as the parent artifact.'
    },
    {
      title: 'Deck AIStack extracts the structure and message',
      detail: 'Slides, text blocks, and classifications are prepared before diligence analysis or Smart Edit becomes available.'
    },
    {
      title: 'Review the investor-ready version',
      detail: 'Suggestions stay reviewable, editable, and auditable before you export or share anything.'
    }
  ];

  const aiConfigured = $derived(aiProviderSummary.isConfigured);
  const providerLabel = $derived(
    aiProviderSummary.provider
      ? aiProviderSummary.provider === 'openai'
        ? 'OpenAI connected'
        : aiProviderSummary.provider === 'openrouter'
          ? 'OpenRouter connected'
          : 'Claude connected'
      : 'Built-in OpenRouter ready'
  );
</script>

<section class="welcome-shell">
  <section class="welcome-frame">
    <section class="panel welcome-hero">
      <div class="welcome-hero__copy">
        <div class="eyebrow">Private workspace</div>
        <h2>{title}</h2>
        <p class="muted">{subtitle}</p>

        <div class="welcome-hero__actions">
          <a class="button" href="#first-deck-upload">Upload first deck</a>
        </div>

        <div class="welcome-hero__trust">
          <span class="pill">{providerLabel}</span>
          <span class="pill">Encrypted workspace key</span>
          <span class="pill">No silent deck overwrites</span>
        </div>
      </div>
    </section>

    <section class="welcome-grid">
      <article class="panel welcome-card">
        <div class="eyebrow">Step 1</div>
        <h3>Upload first deck</h3>
        <p class="muted">Deck AIStack starts with built-in OpenRouter access. You can add OpenAI, OpenRouter, or Claude later for faster responses, your own quota, or provider control.</p>
        <div class="welcome-card__footer">
          <span class:connected={aiConfigured} class="status-dot" aria-hidden="true"></span>
          <span>{aiConfigured ? 'Secure connection saved' : 'Built-in AI ready for first upload'}</span>
        </div>
      </article>

      <article class="panel welcome-card">
        <div class="eyebrow">Your workspace</div>
        <h3>No decks yet</h3>
        <p class="muted">Uploaded decks will appear here as the starting point for diligence review, audience adaptation, Smart Edit, and export.</p>
        <a class="button secondary welcome-card__cta" href="#first-deck-upload">Upload source deck</a>
      </article>
    </section>

    <section class="welcome-frame__primary">
      <UploadFirstDeckCard
        redirectHref="/decks/new"
        on:uploaded={(event) => {
          goto(`/decks/${event.detail.deckId}/smart-deck`);
        }}
      />
    </section>

    <section class="welcome-frame__secondary">
      <article class="panel welcome-secondary__workflow">
        <div class="section-heading">
          <div>
            <div class="eyebrow">What happens next</div>
            <h3>Your first Deck AIStack workflow</h3>
            <p class="muted">The first deck unlocks the full review flow without turning the workspace into a generic presentation builder.</p>
          </div>
        </div>

        <FirstDeckWorkflow />

        <ol class="welcome-next-list">
          {#each nextSteps as step, index}
            <li>
              <span>{index + 1}</span>
              <div>
                <strong>{step.title}</strong>
                <p class="muted">{step.detail}</p>
              </div>
            </li>
          {/each}
        </ol>
      </article>
    </section>
  </section>
</section>

<style>
  .welcome-shell {
    min-width: 0;
  }

  .welcome-frame {
    width: 100%;
    min-width: 0;
    display: grid;
    gap: 1rem;
  }

  h2,
  h3 {
    margin: 0.35rem 0 0;
  }

  .welcome-hero {
    padding: 1.7rem;
    display: grid;
    gap: 1rem;
  }

  .welcome-hero__copy {
    max-width: 60rem;
    display: grid;
    gap: 0.95rem;
  }

  .welcome-hero__actions,
  .welcome-hero__trust {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .welcome-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }

  .welcome-card {
    padding: 1.3rem;
    display: grid;
    gap: 0.8rem;
  }

  .welcome-card__footer {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    color: var(--ink-soft);
  }

  .status-dot {
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 999px;
    background: var(--warn);
    box-shadow: 0 0 0 6px color-mix(in srgb, var(--warn) 18%, transparent);
  }

  .status-dot.connected {
    background: var(--success);
    box-shadow: 0 0 0 6px color-mix(in srgb, var(--success) 18%, transparent);
  }

  .welcome-card__cta {
    width: fit-content;
  }

  .welcome-frame__primary,
  .welcome-frame__secondary {
    min-width: 0;
  }

  .welcome-secondary__workflow {
    padding: 1.35rem;
  }

  .section-heading {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    align-items: end;
  }

  .welcome-secondary__workflow :global(.workflow-grid) {
    margin-top: 1rem;
  }

  .welcome-next-list {
    margin: 1.25rem 0 0;
    padding: 0;
    list-style: none;
    display: grid;
    gap: 1rem;
  }

  .welcome-next-list li {
    display: grid;
    grid-template-columns: 40px minmax(0, 1fr);
    gap: 0.9rem;
    align-items: start;
  }

  .welcome-next-list span {
    width: 40px;
    height: 40px;
    border-radius: 999px;
    display: grid;
    place-items: center;
    background: var(--surface-active);
    color: var(--accent);
    font-weight: 700;
  }

  .welcome-next-list strong,
  .welcome-next-list p {
    display: block;
  }

  .welcome-next-list p {
    margin: 0.3rem 0 0;
  }

  @media (max-width: 1200px) {
    .welcome-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 820px) {
    .welcome-hero,
    .welcome-card,
    .welcome-secondary__workflow {
      padding: 1.15rem;
    }

    .welcome-hero__actions .button,
    .welcome-card__cta {
      width: 100%;
    }
  }
</style>
