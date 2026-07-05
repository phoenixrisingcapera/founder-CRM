<script lang="ts">
  import PublicAuthShell from '$components/PublicAuthShell.svelte';

  let showProviderModal = $state(true);
  let provider = $state<'openai' | 'openrouter' | 'claude'>('openai');

  const providerDetails = {
    openai: {
      name: 'OpenAI',
      title: 'OpenAI connection',
      placeholder: 'sk-...',
      copy: 'Use your OpenAI access for deck understanding, diligence review, and Smart Edit suggestions.',
      models: ['gpt-5', 'gpt-4.1']
    },
    openrouter: {
      name: 'OpenRouter',
      title: 'OpenRouter connection',
      placeholder: 'sk-or-...',
      copy: 'Use your OpenRouter access to route deck understanding, diligence review, and Smart Edit suggestions through your preferred model.',
      models: ['openai/gpt-4o', 'openai/gpt-4.1-mini', 'openai/gpt-4', 'anthropic/claude-sonnet-4.5']
    },
    claude: {
      name: 'Claude',
      title: 'Claude connection',
      placeholder: 'claude-api-key-...',
      copy: 'Use your Claude access for long-context deck understanding, brand extraction support, and guided Smart Edit reasoning.',
      models: ['claude-sonnet-4-5', 'claude-opus-4-1']
    }
  };

  const intakeItems = [
    'Upload deck',
    'Website URL',
    'Optional brand guide',
    'Optional team / LinkedIn inputs'
  ];

  const systemSteps = [
    'Save your deck and company context',
    'Extract company and brand signals',
    'Prepare the Smart Deck workspace',
    'Move into dashboard review'
  ];

  const trustPoints = [
    'Your key stays in your private workspace settings',
    'Every AI suggestion stays reviewable before apply',
    'Deck, website, and brand context remain the source of truth'
  ];
</script>

<PublicAuthShell
  eyebrow="Phase 1"
  title="Create Smart Deck intake"
  subtitle="This is the first required step after sign-in. Add the source material and private AI access needed before you move into the dashboard workspace."
  alternateHref="/dashboard"
  alternateLabel="Already have a deck project?"
  alternateCta="Go to dashboard"
>
  <section class="intake-card">
    <div class="hero-panel">
      <div>
        <strong>What you need to provide</strong>
        <ul>
          {#each intakeItems as item}
            <li>{item}</li>
          {/each}
        </ul>
      </div>

      <div class="phase-panel workflow-panel">
        <strong>What Deck AIStack will do next</strong>
        <ol>
          {#each systemSteps as step}
            <li>{step}</li>
          {/each}
        </ol>
      </div>
    </div>

    <div class="phase-panel trust-panel">
      <strong>Before you continue</strong>
      <p class="note">Connect your preferred AI provider so Deck AIStack can prepare intake, review, and Smart Edit suggestions inside your workspace.</p>
      <div class="trust-list">
        {#each trustPoints as point}
          <span class="trust-pill">{point}</span>
        {/each}
      </div>
    </div>

    <div class="cta-stack">
      <button class="button primary-cta" type="button" onclick={() => (showProviderModal = true)}>Connect AI provider</button>
      <a class="ghost-cta" href="/decks/new">Go to intake form</a>
    </div>
  </section>

  {#if showProviderModal}
    <div class="modal-backdrop" role="presentation">
      <button class="backdrop-dismiss" type="button" aria-label="Close popup" onclick={() => (showProviderModal = false)}></button>
      <div
        class="provider-modal-shell"
        role="dialog"
        aria-modal="true"
        aria-labelledby="provider-modal-title"
      >
        <section class="panel provider-modal">
          <div class="modal-top">
            <div>
              <div class="eyebrow">Workspace AI</div>
              <h2 id="provider-modal-title">Connect an AI provider</h2>
              <p class="muted">Add private AI access now so brand context, deck review, and Smart Edit suggestions can be prepared while you continue through intake.</p>
            </div>
            <button class="close-button" type="button" aria-label="Close popup" onclick={() => (showProviderModal = false)}>×</button>
          </div>

          <div class="provider-tabs">
            <button class:active={provider === 'openai'} type="button" onclick={() => (provider = 'openai')}>OpenAI</button>
            <button class:active={provider === 'openrouter'} type="button" onclick={() => (provider = 'openrouter')}>OpenRouter</button>
            <button class:active={provider === 'claude'} type="button" onclick={() => (provider = 'claude')}>Claude</button>
          </div>

          <div class="provider-grid">
            <div class="phase-panel modal-copy">
              <strong>{providerDetails[provider].title}</strong>
              <p class="note">{providerDetails[provider].copy}</p>
              <ul>
                <li>Stored at workspace level</li>
                <li>Used only for your private deck runs</li>
                <li>Can be changed later in Settings</li>
              </ul>
            </div>

            <form class="phase-panel provider-form">
              <label>
                <span>Provider name</span>
                <input value={providerDetails[provider].name} readonly />
              </label>
              <label>
                <span>Private access key</span>
                <input
                  type="password"
                  placeholder={providerDetails[provider].placeholder}
                />
              </label>
              <label>
                <span>Optional model preference</span>
                <select>
                  {#each providerDetails[provider].models as model}
                    <option>{model}</option>
                  {/each}
                </select>
              </label>

              <div class="modal-actions">
                <button class="ghost-cta" type="button" onclick={() => (showProviderModal = false)}>Maybe later</button>
                <a class="button primary-cta" href="/decks/new">Save and continue</a>
              </div>
            </form>
          </div>
        </section>
      </div>
    </div>
  {/if}
</PublicAuthShell>

<style>
  .intake-card {
    display: grid;
    gap: 1rem;
    position: relative;
  }

  .hero-panel {
    display: grid;
    gap: 1rem;
  }

  .phase-panel {
    border: 1px solid var(--line);
    border-radius: 18px;
    background: rgba(255,255,255,0.03);
    padding: 1rem;
  }

  .workflow-panel {
    border-color: var(--line-strong);
    background: rgba(24, 200, 255, 0.06);
  }

  .trust-panel {
    background: linear-gradient(180deg, rgba(124, 58, 237, 0.12), rgba(255,255,255,0.03));
    border-color: rgba(124, 58, 237, 0.25);
  }

  ul,
  ol {
    margin: 0.8rem 0 0;
    padding-left: 1rem;
    display: grid;
    gap: 0.65rem;
    color: var(--ink-soft);
  }

  .trust-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    margin-top: 0.9rem;
  }

  .trust-pill {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.05);
    padding: 0.55rem 0.8rem;
    color: var(--ink-soft);
    font-size: 0.88rem;
  }

  .cta-stack {
    display: grid;
    gap: 0.75rem;
  }

  .primary-cta,
  .ghost-cta {
    display: grid;
    place-items: center;
    min-height: 54px;
  }

  .ghost-cta {
    border-radius: 16px;
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.02);
    color: var(--ink-strong);
  }

  .note {
    margin: 0.35rem 0 0;
    color: var(--muted);
    font-size: 0.92rem;
    line-height: 1.5;
  }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(5, 11, 31, 0.72);
    backdrop-filter: blur(14px);
    display: grid;
    place-items: center;
    padding: 1.5rem;
    z-index: 50;
  }

  .backdrop-dismiss {
    position: absolute;
    inset: 0;
    border: 0;
    background: transparent;
    padding: 0;
  }

  .provider-modal {
    width: min(920px, 100%);
    padding: 1.35rem;
    display: grid;
    gap: 1rem;
    box-shadow: var(--shadow), var(--shadow-glow-blue);
  }

  .provider-modal-shell {
    width: min(920px, 100%);
    position: relative;
    z-index: 1;
  }

  .modal-top {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
  }

  .modal-top h2 {
    margin: 0.35rem 0 0;
    font-size: clamp(1.8rem, 3vw, 2.5rem);
    letter-spacing: -0.05em;
  }

  .close-button {
    width: 42px;
    height: 42px;
    border-radius: 14px;
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.03);
    color: var(--ink-strong);
    font-size: 1.35rem;
  }

  .provider-tabs {
    display: flex;
    gap: 0.75rem;
  }

  .provider-tabs button {
    min-height: 46px;
    padding: 0.75rem 1rem;
    border-radius: 14px;
    border: 1px solid var(--line);
    background: transparent;
    color: var(--ink-soft);
  }

  .provider-tabs button.active {
    background: linear-gradient(135deg, rgba(24, 200, 255, 0.16), rgba(124, 58, 237, 0.16));
    color: var(--ink-strong);
    border-color: var(--line-strong);
  }

  .provider-grid {
    display: grid;
    grid-template-columns: 0.95fr 1.05fr;
    gap: 1rem;
  }

  .modal-copy,
  .provider-form {
    display: grid;
    gap: 0.9rem;
  }

  .provider-form label {
    display: grid;
    gap: 0.45rem;
  }

  .provider-form input,
  .provider-form select {
    border-radius: 14px;
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.03);
    color: var(--ink);
    padding: 0.9rem 1rem;
  }

  .modal-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
    margin-top: 0.2rem;
  }

  @media (max-width: 820px) {
    .provider-grid,
    .modal-actions {
      grid-template-columns: 1fr;
    }

    .modal-top {
      align-items: start;
    }
  }
</style>
