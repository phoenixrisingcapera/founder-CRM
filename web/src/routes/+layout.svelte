<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { ensureSession, reportFailureTicket } from '$lib/api';
  import { authReady, session } from '$lib/stores/session';

  const links = [
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/people', label: 'People' },
    { href: '/companies', label: 'Companies' },
    { href: '/projects', label: 'Projects' },
    { href: '/dispatches', label: 'Dispatches' },
    { href: '/warm-path', label: 'Warm Path' },
    { href: '/opportunities', label: 'Opportunities' },
    { href: '/relationship-graph', label: 'Relationship Graph' },
    { href: '/deck-assistant', label: 'Deck Assistant' },
    { href: '/artifacts', label: 'Artifacts' },
    { href: '/settings', label: 'Settings' },
    { href: '/admin', label: 'Admin' }
  ];

  let error = '';

  onMount(() => {
    const handleWindowError = (event: ErrorEvent) => {
      void reportFailureTicket({
        route: $page.route.id,
        page_url: window.location.href,
        status_code: null,
        error_name: event.error?.name || 'WindowError',
        error_message: event.message || 'Unhandled window error',
        error_stack: event.error?.stack || null,
        severity: 'medium',
        source: 'frontend',
        context: { pathname: window.location.pathname }
      }).catch(() => null);
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason instanceof Error ? event.reason : null;
      void reportFailureTicket({
        route: $page.route.id,
        page_url: window.location.href,
        status_code: null,
        error_name: reason?.name || 'UnhandledRejection',
        error_message: reason?.message || String(event.reason || 'Unhandled promise rejection'),
        error_stack: reason?.stack || null,
        severity: 'medium',
        source: 'frontend',
        context: { pathname: window.location.pathname }
      }).catch(() => null);
    };

    window.addEventListener('error', handleWindowError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    void (async () => {
      try {
        session.set(await ensureSession());
        authReady.set(true);
      } catch (err) {
        session.set(null);
        authReady.set(true);
        error = err instanceof Error ? err.message : 'Could not start your workspace.';
        if (!$page.url.pathname.startsWith('/auth')) {
          goto('/auth');
        }
      }
    })();

    return () => {
      window.removeEventListener('error', handleWindowError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  });

  $: if ($authReady && !$session && !$page.url.pathname.startsWith('/auth')) {
    goto('/auth');
  }
</script>

<svelte:head>
  <title>AiStack Founder CRM</title>
</svelte:head>

<div class="app-shell">
  <aside class="sidebar">
    <div style="margin-bottom:2rem;">
      <div class="eyebrow">AiStack</div>
      <h1 style="margin:0.35rem 0 0.5rem 0; font-size:1.35rem;">Founder CRM</h1>
      <p class="muted" style="margin:0;">Owned fundraising workflow for founder-led investor execution.</p>
    </div>

    {#if $session}
      <nav>
        {#each links as link}
          <a class:active={$page.url.pathname === link.href} class="nav-link" href={link.href}>{link.label}</a>
        {/each}
      </nav>
    {/if}

    <div class="panel" style="margin-top:2rem; padding:1rem;">
      <div class="eyebrow">Workspace</div>
      {#if $session}
        <div style="font-weight:600; margin-top:0.25rem;">{$session.workspace.name}</div>
        <div class="muted" style="font-size:0.9rem; margin-top:0.35rem;">{$session.user.full_name}</div>
      {:else if error}
        <div class="muted" style="margin-top:0.35rem;">{error}</div>
      {:else}
        <div class="muted" style="margin-top:0.35rem;">Sign in to continue.</div>
      {/if}
    </div>
  </aside>

  <main class="content">
    <slot />
  </main>
</div>
