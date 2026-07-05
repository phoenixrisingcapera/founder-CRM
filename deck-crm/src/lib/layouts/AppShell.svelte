<script lang="ts">
  import { browser } from '$app/environment';
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import RouteProgress from '$components/RouteProgress.svelte';
  import MobileAppGate from '$lib/layouts/MobileAppGate.svelte';
  import { sessionState } from '$lib/stores/session';
  import { theme } from '$lib/stores/theme';
  import { isMobileViewport } from '$lib/stores/viewport';

  let { children }: { children: import('svelte').Snippet } = $props();

  const deckWorkspaceRoute = $derived(/^\/decks\/[^/]+(?:\/|$)/.test(page.url.pathname));
  const uploadRoute = $derived(/^\/decks\/new(?:\/|$)/.test(page.url.pathname));
  const gateForMobile = $derived(deckWorkspaceRoute && !uploadRoute);

  if (browser) {
    theme.prime('dark');
  }

  onMount(() => {
    sessionState.load();
  });
</script>

<div class="app-route-shell" data-sveltekit-preload-data="off">
  <RouteProgress />
  <MobileAppGate enabled={$isMobileViewport && gateForMobile}>
    <div class="app-shell-region">
      {@render children()}
    </div>
  </MobileAppGate>
</div>
