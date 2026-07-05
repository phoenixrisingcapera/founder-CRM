<script lang="ts">
  import { goto } from '$app/navigation';
  import type { DesignBatchPreview } from '@deck-aistack-codes/shared';
  import AppLogo from '$components/AppLogo.svelte';
  import DeckAiChatPopup from '$components/deck-shell/DeckAiChatPopup.svelte';
  import UtilitiesBar from '$components/UtilitiesBar.svelte';
  import { sessionState } from '$lib/stores/session';
  import type { AiDesignCommand, AiDesignPreset } from '$lib/types/ai-design';

  interface Props {
    active?: string;
    currentDeckId?: string | null;
    latestBatches?: DesignBatchPreview[];
    showUtilities?: boolean;
    compact?: boolean;
  }

  let { active = '', currentDeckId = null, latestBatches = [], showUtilities = true, compact = false }: Props = $props();
  let deckWorkflowExpanded = $state(true);
  let iterationsExpanded = $state(false);
  let assistantOpen = $state(false);
  let assistantTarget = $state<'current_slide' | 'selected_slides' | 'whole_deck'>('whole_deck');
  let assistantInstruction = $state('Create a cleaner investor-ready version of this deck.');
  let assistantPreset = $state<AiDesignPreset | null>('investor_ready');

  const allMainItems = [
    { href: '/welcome', label: 'Welcome', key: 'welcome', icon: '◎' },
    { href: '/decks', label: 'Decks', key: 'decks', icon: '▣' },
    { href: '/decks/new', label: 'Upload Deck', key: 'upload', icon: '⇪' }
  ];

  const allLibraryItems = [
    { href: '/decks', label: 'Select a deck', key: 'deck-select', icon: '▣' }
  ];

  const allDeckItems = [
    { suffix: '/smart-deck', label: 'Smart Deck', key: 'smart-deck', icon: '◫' },
    { suffix: '/smart-edit', label: 'Smart Edit', key: 'smart-edit', icon: '✎' },
    { suffix: '/due-diligence', label: 'Due Diligence', key: 'diligence', icon: '◌' },
    { suffix: '/batches', label: 'Iterations', key: 'batches', icon: '◭' },
    { suffix: '/export', label: 'Exports', key: 'exports', icon: '⇩' }
  ];

  const isWelcomeSidebar = $derived(active === 'welcome');
  const showSidebarUtilities = $derived(showUtilities && !isWelcomeSidebar && active !== 'upload');
  const isAdmin = $derived(
    $sessionState.permissions.includes('admin:access') ||
      $sessionState.user?.role === 'super_admin' ||
      $sessionState.user?.role === 'admin'
  );

  const mainItems = $derived(
    [
      ...allMainItems.filter((item) => {
        if (isWelcomeSidebar) return item.key === 'welcome';
        return item.key === 'upload' ? $sessionState.permissions.includes('deck:create') : true;
      }),
      ...(currentDeckId && !isWelcomeSidebar
        ? [{ href: `/decks/${currentDeckId}/smart-deck`, label: 'Smart Deck', key: 'smart-deck', icon: '◫' }]
        : [])
    ]
  );

  const libraryItems = $derived(
    isWelcomeSidebar
      ? []
      : allLibraryItems.map((item) =>
          item.key === 'diligence'
            ? { ...item, href: currentDeckId ? `/decks/${currentDeckId}/due-diligence` : '/decks' }
            : item
        )
  );

  const deckItems = $derived(
    isWelcomeSidebar
      ? []
      : allDeckItems.filter((item) => (item.key === 'exports' ? $sessionState.permissions.includes('deck:export') : true))
  );
  const adminReviewItems = $derived(
    isWelcomeSidebar || !isAdmin
      ? []
      : [
          { href: '/admin/elements', label: 'Elements', key: 'admin', icon: '◆' },
          {
            href: currentDeckId ? `/admin/processing/${currentDeckId}` : '/decks',
            label: 'Processing',
            key: 'admin-processing',
            icon: '◇'
          },
          {
            href: currentDeckId ? `/admin/slides/${currentDeckId}` : '/decks',
            label: 'Parsed slides',
            key: 'admin-slides',
            icon: '▦'
          },
          { href: '/admin', label: 'Admin console', key: 'admin-console', icon: '⌁' },
          { href: '/admin/failure-tickets', label: 'Failure tickets', key: 'admin-failure-tickets', icon: '⚠' },
          { href: '/admin/users', label: 'Users', key: 'admin-users', icon: '◉' },
          { href: '/insights', label: 'Insights', key: 'insights', icon: '⌁' },
          { href: '/team', label: 'Team', key: 'team', icon: '◯' },
          { href: '/settings/account/settings', label: 'Account settings', key: 'account-settings', icon: '⚙' },
          { href: '/settings/account/connected-accounts', label: 'Connected accounts', key: 'connected-accounts', icon: '⧉' }
        ]
  );
  const hasDeckWorkflow = $derived(Boolean(currentDeckId) && deckItems.length > 0);
  const sortedIterations = $derived(
    [...latestBatches].sort((a, b) => {
      const byDate = new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      return byDate || b.batchNumber - a.batchNumber;
    })
  );
  const visibleIterations = $derived(sortedIterations.slice(0, iterationsExpanded ? 8 : 3));
  const hasGeneratedIterations = $derived(sortedIterations.length > 0);
  const canToggleIterations = $derived(sortedIterations.length > 3);
  const canExportCurrentDeck = $derived(Boolean(currentDeckId) && $sessionState.permissions.includes('deck:export'));

  function deckHref(suffix: string) {
    return currentDeckId ? `/decks/${currentDeckId}${suffix}` : '/decks';
  }

  function iterationHref(batchId: string) {
    return currentDeckId ? `/decks/${currentDeckId}/batches/${batchId}` : '/decks';
  }

  function iterationLabel(batch: DesignBatchPreview) {
    return `Iteration ${batch.batchNumber}`;
  }

  function iterationMeta(batch: DesignBatchPreview) {
    if (batch.batchName) return batch.batchName;
    if (batch.scopeType === 'whole_deck') return 'Whole deck';
    return `${batch.selectedSlideCount} slides`;
  }

  function isItemActive(itemKey: string) {
    if (itemKey === 'welcome' && active === 'welcome-back') {
      return true;
    }

    if (itemKey === 'settings' && !isAdmin && (active === 'account-settings' || active === 'connected-accounts')) {
      return true;
    }

    return active === itemKey;
  }

  function openAssistantWorkspace(command?: AiDesignCommand) {
    assistantOpen = false;
    const query = new URLSearchParams();
    query.set('assistant', '1');
    query.set('scope', command?.scope ?? assistantTarget);
    if (command?.preset ?? assistantPreset) query.set('preset', command?.preset ?? assistantPreset ?? '');
    if ((command?.command ?? assistantInstruction).trim()) query.set('instruction', (command?.command ?? assistantInstruction).trim());

    void goto(currentDeckId ? `/decks/${currentDeckId}/smart-edit?${query}` : '/decks/new');
  }

  $effect(() => {
    if (!currentDeckId) {
      deckWorkflowExpanded = false;
      return;
    }

    if (
      active === 'smart-deck' ||
      active === 'smart-edit' ||
      active === 'diligence' ||
      active === 'batches' ||
      active === 'exports' ||
      active.startsWith('batch:')
    ) {
      deckWorkflowExpanded = true;
    }
  });
</script>

<aside class:app-sidebar--compact={compact} class="app-sidebar">
  <div class="app-sidebar__brand">
    <AppLogo alt="Deck AIStack logo" />
    <div class="app-sidebar__brand-copy">
      <strong>Deck AIStack</strong>
      <p>AI deck infrastructure</p>
    </div>
  </div>

  <a class="app-sidebar__cta" href="/decks/new" title="New deck" aria-label="New deck" aria-current={active === 'upload' ? 'page' : undefined}><span aria-hidden={compact}>+</span><span class="app-sidebar__item-label">New deck</span></a>

  {#if canExportCurrentDeck}
    <nav class="app-sidebar__mobile-export" aria-label="Mobile export navigation">
      <a href={deckHref('/export')} class:active={isItemActive('exports')} aria-current={isItemActive('exports') ? 'page' : undefined}>
        <span>⇩</span>
        <span>Export</span>
      </a>
    </nav>
  {/if}

  <div class="app-sidebar__label">Main</div>
  <nav class="app-sidebar__nav">
    {#each mainItems as item}
      <a href={item.href} class:active={isItemActive(item.key)} title={compact ? item.label : undefined} aria-label={compact ? item.label : undefined} aria-current={isItemActive(item.key) ? 'page' : undefined}>
        <span>{item.icon}</span>
        <span class="app-sidebar__item-label">{item.label}</span>
      </a>
    {/each}
  </nav>

  {#if libraryItems.length > 0}
    <div class="app-sidebar__label">Workspace</div>
    <nav class="app-sidebar__nav">
      {#each libraryItems as item}
        <a href={item.href} class:active={isItemActive(item.key)} title={compact ? item.label : undefined} aria-label={compact ? item.label : undefined} aria-current={isItemActive(item.key) ? 'page' : undefined}>
          <span>{item.icon}</span>
          <span class="app-sidebar__item-label">{item.label}</span>
        </a>
      {/each}
    </nav>
  {/if}

  {#if hasDeckWorkflow}
    <button class="app-sidebar__section-toggle" type="button" onclick={() => (deckWorkflowExpanded = !deckWorkflowExpanded)}>
      <span class="app-sidebar__label">Deck workflow</span>
      <span class:expanded={deckWorkflowExpanded} class="app-sidebar__chevron">⌄</span>
    </button>

    {#if deckWorkflowExpanded}
      <nav class="app-sidebar__nav">
        {#each deckItems as item}
          <div class="app-sidebar__nav-group">
            <a href={deckHref(item.suffix)} class:active={isItemActive(item.key)} title={compact ? item.label : undefined} aria-label={compact ? item.label : undefined} aria-current={isItemActive(item.key) ? 'page' : undefined}>
              <span>{item.icon}</span>
              <span class="app-sidebar__item-label">{item.label}</span>
            </a>

            {#if item.key === 'batches' && currentDeckId && hasGeneratedIterations}
              <div class="app-sidebar__iterations" aria-label="Generated iterations">
                <div class="app-sidebar__iterations-head">
                  <span>Iterations</span>
                  <small>{sortedIterations.length}</small>
                </div>
                <div class="app-sidebar__iteration-list">
                  {#each visibleIterations as batch}
                    <a
                      href={iterationHref(batch.id)}
                      class="app-sidebar__iteration-link"
                      class:active={active === `batch:${batch.id}`}
                      title={batch.batchName ?? iterationLabel(batch)}
                      aria-current={active === `batch:${batch.id}` ? 'page' : undefined}
                    >
                      <span class="app-sidebar__iteration-title">{iterationLabel(batch)}</span>
                      <small>{iterationMeta(batch)}</small>
                    </a>
                  {/each}
                </div>
                {#if canToggleIterations}
                  <button class="app-sidebar__iteration-toggle" type="button" onclick={() => (iterationsExpanded = !iterationsExpanded)}>
                    {iterationsExpanded ? 'Show less' : `Show ${Math.min(sortedIterations.length, 8) - 3} more`}
                  </button>
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      </nav>
    {/if}
  {/if}

  {#if adminReviewItems.length > 0}
    <div class="app-sidebar__label">Admin review</div>
    <nav class="app-sidebar__nav">
      {#each adminReviewItems as item}
        <a href={item.href} class:active={isItemActive(item.key)} aria-current={isItemActive(item.key) ? 'page' : undefined}>
          <span>{item.icon}</span>
          <span class="app-sidebar__item-label">{item.label}</span>
        </a>
      {/each}
    </nav>
  {/if}

  {#if !isWelcomeSidebar}
    <button
      type="button"
      class="app-sidebar__assistant-trigger"
      aria-haspopup="dialog"
      aria-expanded={assistantOpen}
      title={compact ? 'Assistant' : undefined}
      aria-label={compact ? 'Assistant' : undefined}
      onclick={() => {
        assistantOpen = true;
      }}
    >
      <span class="app-sidebar__assistant-icon">AI</span>
      <span class="app-sidebar__item-label">Assistant</span>
    </button>
  {/if}

  <DeckAiChatPopup
    open={assistantOpen}
    deckTitle="Current deck"
    selectedSlideCount={0}
    target={assistantTarget}
    instruction={assistantInstruction}
    preset={assistantPreset}
    onClose={() => {
      assistantOpen = false;
    }}
    onTargetChange={(nextTarget) => {
      assistantTarget = nextTarget;
    }}
    onInstructionChange={(nextInstruction) => {
      assistantInstruction = nextInstruction;
    }}
    onPresetChange={(nextPreset) => {
      assistantPreset = nextPreset;
    }}
    onCreateVersion={openAssistantWorkspace}
  />

  {#if showSidebarUtilities}
    <div class="app-sidebar__footer">
      <div class="app-sidebar__user">
        <div class="app-avatar">AM</div>
        <div class="app-sidebar__user-copy">
          <strong>{$sessionState.user?.email?.split('@')[0] ?? 'Alex Morgan'}</strong>
          <p>{$sessionState.user?.email ?? 'alex@morgan.vc'}</p>
        </div>
      </div>
      <UtilitiesBar />
    </div>
  {/if}
</aside>
