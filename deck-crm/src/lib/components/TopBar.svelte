<script lang="ts">
  import { onMount } from 'svelte';
  import StatusBadge from '$components/StatusBadge.svelte';
  import ThemeToggle from '$components/ThemeToggle.svelte';
  import WorkspaceAiProviderModal from '$components/WorkspaceAiProviderModal.svelte';
  import { sessionState } from '$lib/stores/session';
  import { loadWorkspaceAiProviderSummary, workspaceAiProviderStore, setWorkspaceAiProviderSummary } from '$lib/stores/workspaceAiProvider';
  import type { WorkspaceAiProviderRouteResponse } from '@deck-aistack-codes/shared';

  interface Props {
    title: string;
    subtitle?: string;
    status?: string;
    showTopBarCopy?: boolean;
    compactTopBar?: boolean;
    showTopBarSearch?: boolean;
    deckLabel?: string;
    actions?: import('svelte').Snippet;
    headerExtension?: import('svelte').Snippet;
  }

  let {
    title,
    subtitle = '',
    status = '',
    showTopBarCopy = true,
    compactTopBar = false,
    showTopBarSearch = true,
    deckLabel = 'Deck AIStack Workspace',
    actions,
    headerExtension
  }: Props = $props();

  let searchOpen = $state(false);
  let providerModalOpen = $state(false);

  function providerLabel(summary: WorkspaceAiProviderRouteResponse['summary'] | null) {
    if (!summary?.isConfigured || !summary.provider) return 'Built-in AI';
    if (summary.provider === 'openai') return 'OpenAI connected';
    if (summary.provider === 'openrouter') return 'OpenRouter connected';
    return 'Claude connected';
  }

  function userInitials() {
    const email = $sessionState.user?.email ?? '';
    if (!email) return 'AC';
    return email.slice(0, 2).toUpperCase();
  }

  onMount(() => {
    void loadWorkspaceAiProviderSummary();
  });
</script>

<header class:app-topbar--compact={compactTopBar} class="app-topbar">
  <WorkspaceAiProviderModal
    forceOpen={providerModalOpen}
    on:configured={(event) => {
      setWorkspaceAiProviderSummary(event.detail);
      providerModalOpen = false;
    }}
    on:skipped={(event) => {
      setWorkspaceAiProviderSummary(event.detail);
      providerModalOpen = false;
    }}
  />

  <div class="app-topbar__utility" aria-label="Workspace utilities">
    {#if showTopBarCopy}
      <div class="app-topbar__page">
        <div class="app-topbar__page-meta">
          <span class="app-topbar__chip">{deckLabel}</span>
          {#if status}
            <StatusBadge {status} />
          {/if}
        </div>
        <div class="app-topbar__page-copy">
          <strong>{title}</strong>
          {#if subtitle}
            <span>{subtitle}</span>
          {/if}
        </div>
      </div>
    {/if}

    <div class="app-topbar__utility-actions">
      <button
        class="app-topbar__utility-link app-topbar__utility-link--button app-topbar__utility-link--ai"
        type="button"
        onclick={() => {
          providerModalOpen = true;
        }}
      >
        {providerLabel($workspaceAiProviderStore)}
      </button>
      <a class="app-topbar__utility-link" href="/app/billing">
        {$sessionState.billingPlan === 'pro' ? 'Pro plan' : 'Upgrade'}
      </a>
      <a class="app-topbar__utility-link" href="/settings">Settings</a>
      <ThemeToggle compact={true} />
    </div>
  </div>

  <div class:app-topbar__command--compact={compactTopBar} class="app-topbar__command panel">
    {#if showTopBarSearch}
      <div class:open={searchOpen} class="app-topbar__search">
        <button
          type="button"
          class="app-topbar__search-trigger"
          aria-label="Open search"
          aria-expanded={searchOpen}
          onclick={() => {
            searchOpen = !searchOpen;
          }}
        >
          <span aria-hidden="true">⌕</span>
        </button>
        <label class="app-topbar__search-panel">
          <span>Search decks, slides, or block text...</span>
          <input type="search" placeholder="Search decks, slides, or content..." />
        </label>
      </div>
    {/if}

    <div class="app-topbar__right">
      {#if actions}
        <div class="app-topbar__actions">{@render actions()}</div>
      {/if}
      <button class:app-topbar__icon--compact={compactTopBar} type="button" class="app-topbar__icon" aria-label="Notifications">1</button>
      <button
        class:app-topbar__menu--compact={compactTopBar}
        type="button"
        class="app-topbar__menu"
        aria-label={`User menu for ${$sessionState.user?.email ?? 'current user'}`}
        title={$sessionState.user?.email ?? 'User menu'}
      >
        <span class="app-avatar">{userInitials()}</span>
      </button>
    </div>
  </div>

  {#if headerExtension}
    <div class="app-topbar__extension panel">
      {@render headerExtension()}
    </div>
  {/if}
</header>
