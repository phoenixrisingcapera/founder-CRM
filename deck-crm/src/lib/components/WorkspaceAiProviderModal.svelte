<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { deckServiceClient } from '$lib/api/deckServiceClient';
  import {
    loadWorkspaceAiProviderSummary,
    setWorkspaceAiProviderSummary
  } from '$lib/stores/workspaceAiProvider';
  import type { WorkspaceAiProvider, WorkspaceAiProviderRouteResponse } from '@deck-aistack-codes/shared';

  const dispatch = createEventDispatcher<{
    configured: WorkspaceAiProviderRouteResponse['summary'];
    skipped: WorkspaceAiProviderRouteResponse['summary'];
  }>();

  interface Props {
    forceOpen?: boolean;
  }

  let { forceOpen = true }: Props = $props();

  let open = $state(false);
  let loadingState = $state<'booting' | 'idle' | 'saving'>('booting');
  let provider = $state<WorkspaceAiProvider>('claude');
  let preferredModel = $state('claude-sonnet-4-5');
  let apiKey = $state('');
  let errorMsg = $state('');

  const providerModels: Record<WorkspaceAiProvider, string[]> = {
    openai: ['gpt-5', 'gpt-4.1'],
    openrouter: ['openai/gpt-4o', 'openai/gpt-4.1-mini', 'openai/gpt-4', 'anthropic/claude-sonnet-4.5'],
    claude: ['claude-sonnet-4-5', 'claude-opus-4-1']
  };

  const providerCopy: Record<WorkspaceAiProvider, { name: string; placeholder: string; defaultModel: string }> = {
    openai: { name: 'OpenAI', placeholder: 'sk-...', defaultModel: 'gpt-5' },
    openrouter: { name: 'OpenRouter', placeholder: 'sk-or-...', defaultModel: 'openai/gpt-4o' },
    claude: { name: 'Claude', placeholder: 'claude-api-key-...', defaultModel: 'claude-sonnet-4-5' }
  };

  onMount(async () => {
    open = forceOpen;

    try {
      const summary = await loadWorkspaceAiProviderSummary();

      if (summary?.provider) {
        provider = summary.provider;
      }

      if (summary?.preferredModel) {
        preferredModel = summary.preferredModel;
      }

      if (summary?.isConfigured && !forceOpen) {
        open = false;
      }
    } catch {
      errorMsg = 'Could not load workspace AI configuration.';
    } finally {
      loadingState = 'idle';
    }
  });

  $effect(() => {
    if (forceOpen) {
      open = true;
    }
  });

  async function dismissForNow() {
    open = false;
    await persist(true);
  }

  async function persist(skipForNow = false) {
    errorMsg = '';
    loadingState = 'saving';

    try {
      const response = await deckServiceClient.saveWorkspaceAiProvider({
        provider,
        apiKey,
        preferredModel,
        skipForNow
      });

      setWorkspaceAiProviderSummary(response.summary);
      apiKey = '';
      open = false;
      dispatch(skipForNow ? 'skipped' : 'configured', response.summary);
    } catch (error) {
      errorMsg = error instanceof Error ? error.message : 'Could not save workspace AI configuration.';
    } finally {
      loadingState = 'idle';
    }
  }
</script>

{#if open}
  <div class="modal-backdrop" role="presentation">
    <div class="provider-modal-shell" role="dialog" aria-modal="true" aria-labelledby="workspace-ai-modal-title">
      <section class="panel provider-modal">
        <header class="modal-top">
          <div class="modal-copy">
            <div class="eyebrow">Workspace access</div>
            <h2 id="workspace-ai-modal-title">Connect your AI provider</h2>
            <p class="muted">Connect an AI provider for this workspace. Deck AIStack tests the key before saving, encrypts it at rest, and then uses that workspace credential for live deck analysis, Smart Edit, and generation.</p>
          </div>

          <button class="dismiss-button" type="button" onclick={dismissForNow} disabled={loadingState === 'saving'}>
            Maybe later
          </button>
        </header>

        <div class="provider-tabs">
          <button class:active={provider === 'openai'} type="button" onclick={() => { provider = 'openai'; preferredModel = providerCopy.openai.defaultModel; }}>
            OpenAI
          </button>
          <button class:active={provider === 'openrouter'} type="button" onclick={() => { provider = 'openrouter'; preferredModel = providerCopy.openrouter.defaultModel; }}>
            OpenRouter
          </button>
          <button class:active={provider === 'claude'} type="button" onclick={() => { provider = 'claude'; preferredModel = providerCopy.claude.defaultModel; }}>
            Claude
          </button>
        </div>

        <form class="provider-form" onsubmit={(event) => { event.preventDefault(); persist(false); }}>
          <label>
            <span>API key</span>
            <input
              type="password"
              bind:value={apiKey}
              placeholder={providerCopy[provider].placeholder}
            />
          </label>

          <label>
            <span>Optional model preference</span>
            <select bind:value={preferredModel}>
              {#each providerModels[provider] as model}
                <option value={model}>{model}</option>
              {/each}
            </select>
          </label>

          <p class="trust-note">Deck AIStack sends a live {providerCopy[provider].name} connection check before storing the key. The saved credential is encrypted at rest and used by secure AI routes for this workspace.</p>

          {#if errorMsg}
            <p class="error-copy">{errorMsg}</p>
          {/if}

          <div class="modal-actions">
            <button class="button primary-cta" type="submit" disabled={loadingState !== 'idle' || !apiKey.trim()}>
              {loadingState === 'saving' ? 'Connecting...' : 'Save and connect'}
            </button>
          </div>
        </form>
      </section>
    </div>
  </div>
{/if}

<style>
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

  .provider-modal-shell {
    width: min(560px, 100%);
    position: relative;
  }

  .provider-modal {
    width: min(560px, 100%);
    padding: 1.5rem;
    display: grid;
    gap: 1.1rem;
    box-shadow: var(--shadow);
  }

  .modal-top {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
  }

  .modal-copy {
    display: grid;
    gap: 0.45rem;
  }

  h2 {
    margin: 0;
    font-size: clamp(1.7rem, 3vw, 2.1rem);
    letter-spacing: -0.04em;
  }

  .dismiss-button {
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-soft);
    color: var(--ink-soft);
    min-height: 42px;
    padding: 0.7rem 1rem;
    white-space: nowrap;
  }

  .provider-tabs {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.65rem;
  }

  .provider-tabs button {
    min-height: 52px;
    padding: 0.85rem 1rem;
    border-radius: 16px;
    border: 1px solid var(--line);
    background: var(--surface-soft);
    color: var(--ink);
    font-weight: 600;
  }

  .provider-tabs button.active {
    background: var(--surface-active);
    color: var(--ink-strong);
    border-color: var(--line-strong);
  }

  .provider-form {
    display: grid;
    gap: 1rem;
  }

  .provider-form label {
    display: grid;
    gap: 0.45rem;
    color: var(--ink-soft);
    font-size: 0.95rem;
  }

  .provider-form input,
  .provider-form select {
    border-radius: 16px;
    border: 1px solid var(--line);
    background: var(--surface-input);
    color: var(--ink);
    padding: 0.9rem 1rem;
  }

  .trust-note {
    margin: 0;
    color: var(--muted);
    font-size: 0.9rem;
    line-height: 1.55;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
  }

  .error-copy {
    margin: 0;
    color: var(--danger);
  }

  @media (max-width: 720px) {
    .modal-backdrop {
      padding: 1rem 0.85rem;
    }

    .modal-top {
      flex-direction: column;
      align-items: stretch;
    }

    .modal-actions .button {
      width: 100%;
    }
  }
</style>
