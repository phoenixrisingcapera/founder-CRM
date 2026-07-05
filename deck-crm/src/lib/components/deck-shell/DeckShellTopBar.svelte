<script lang="ts">
  import type { DesignBatchPreview } from '@deck-aistack-codes/shared';
  import type { Deck } from '$types/domain';

  interface Props {
    deck: Deck;
    mode: 'play' | 'edit' | 'preview';
    latestBatch?: DesignBatchPreview | null;
    readOnlyMode?: boolean;
    backHref?: string;
    backLabel?: string;
    showPropertiesButton?: boolean;
    onModeChange?: (mode: 'play' | 'edit' | 'preview') => void;
    onOpenProperties?: () => void;
  }

  let {
    deck,
    mode,
    latestBatch = null,
    readOnlyMode = false,
    backHref = '/dashboard',
    backLabel = 'Dashboard',
    showPropertiesButton = true,
    onModeChange,
    onOpenProperties
  }: Props = $props();

  const shellModes = ['play', 'edit', 'preview'] as const;
</script>

<header class="deck-shell-topbar panel">
  <div class="deck-shell-topbar__left">
    <a class="deck-shell-topbar__back" href={backHref}>← {backLabel}</a>
    <div class="deck-shell-topbar__title">
      <div class="eyebrow">Interactive shell</div>
      <h2>{deck.title}</h2>
    </div>
  </div>

  <div class="deck-shell-topbar__center">
    {#if readOnlyMode}
      <span class="pill">Read-only</span>
    {/if}
    <span class="pill">Workspace ready</span>
    <span class="pill">Brand ready</span>
    <span class="pill">{latestBatch ? `Version ${latestBatch.batchNumber}` : 'Version 0'}</span>
    <span class="pill">{deck.status}</span>
  </div>

  <div class="deck-shell-topbar__right">
    <div class="deck-shell-topbar__mode-toggle">
      {#each shellModes as shellMode}
        <button
          type="button"
          class:active={mode === shellMode}
          onclick={() => {
            onModeChange?.(shellMode);
          }}
        >
          {shellMode}
        </button>
      {/each}
    </div>

    {#if showPropertiesButton}
      <button type="button" class="button secondary" onclick={() => onOpenProperties?.()}>
        Deck properties
      </button>
    {/if}
  </div>
</header>

<style>
  .deck-shell-topbar {
    padding: 1rem 1.1rem;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    gap: 1rem;
    align-items: center;
  }

  .deck-shell-topbar__left,
  .deck-shell-topbar__center,
  .deck-shell-topbar__right {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .deck-shell-topbar__title h2 {
    margin: 0.2rem 0 0;
    font-size: 1.35rem;
    letter-spacing: -0.04em;
  }

  .deck-shell-topbar__back {
    color: var(--muted);
    font-size: 0.92rem;
  }

  .deck-shell-topbar__mode-toggle {
    display: inline-grid;
    grid-auto-flow: column;
    gap: 0.35rem;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: var(--surface-soft);
    padding: 0.25rem;
  }

  .deck-shell-topbar__mode-toggle button {
    border: 0;
    border-radius: 999px;
    background: transparent;
    color: var(--muted);
    padding: 0.55rem 0.9rem;
  }

  .deck-shell-topbar__mode-toggle button.active {
    background: var(--surface-input);
    color: var(--ink-strong);
    box-shadow: var(--shadow-glow-blue);
  }

  @media (max-width: 1180px) {
    .deck-shell-topbar {
      grid-template-columns: 1fr;
    }
  }
</style>
