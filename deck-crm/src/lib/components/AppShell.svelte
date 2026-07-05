<script lang="ts">
  import type { DesignBatchPreview } from '@deck-aistack-codes/shared';
  import Sidebar from '$components/Sidebar.svelte';
  import TopBar from '$components/TopBar.svelte';
  import UtilitiesBar from '$components/UtilitiesBar.svelte';

  interface Props {
    title: string;
    subtitle?: string;
    activeNav?: string;
    status?: string;
    showTopBar?: boolean;
    showFooterUtilities?: boolean;
    showTopBarCopy?: boolean;
    compactTopBar?: boolean;
    compactSidebar?: boolean;
    showTopBarSearch?: boolean;
    deckLabel?: string;
    currentDeckId?: string | null;
    latestBatches?: DesignBatchPreview[];
    actions?: import('svelte').Snippet;
    headerExtension?: import('svelte').Snippet;
    children?: import('svelte').Snippet;
  }

  let {
    title,
    subtitle = '',
    activeNav = 'dashboard',
    status = '',
    showTopBar = true,
    showFooterUtilities = false,
    showTopBarCopy = true,
    compactTopBar = false,
    compactSidebar = false,
    showTopBarSearch = true,
    deckLabel = 'Deck AIStack Workspace',
    currentDeckId = null,
    latestBatches = [],
    actions,
    headerExtension,
    children
  }: Props = $props();
</script>

<div class="app-shell" class:app-shell--compact-sidebar={compactSidebar}>
  <Sidebar active={activeNav} {currentDeckId} {latestBatches} showUtilities={false} compact={compactSidebar} />
  <div class="app-main">
    {#if showTopBar}
      <TopBar {title} {subtitle} {status} {showTopBarCopy} {compactTopBar} {showTopBarSearch} {deckLabel} {actions} {headerExtension} />
    {/if}
    <main class="app-content">{@render children?.()}</main>
    {#if showFooterUtilities && !showTopBar}
      <div class="app-shell__footer-utilities">
        <UtilitiesBar />
      </div>
    {/if}
  </div>
</div>
