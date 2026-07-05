<script lang="ts">
  import AppLogo from '$components/AppLogo.svelte';
  import ThemeToggle from '$components/ThemeToggle.svelte';
  import { sessionState } from '$lib/stores/session';

  const connectedLabel = $derived.by(() => {
    if ($sessionState.status === 'loading') return 'Checking session';
    if ($sessionState.inspection?.active) return 'Founder inspection';
    if ($sessionState.user) return 'Connected';
    return 'Signed out';
  });

  const identityLabel = $derived(
    $sessionState.user?.id ?? $sessionState.user?.email?.split('@')[0] ?? 'Not signed in'
  );
  const roleLabel = $derived($sessionState.user?.role ?? 'Anonymous');
  const avatarLabel = $derived($sessionState.user?.email?.slice(0, 2).toUpperCase() ?? '--');
</script>

<div class="app-utilities">
  <div class="app-utilities__brand">
    <AppLogo size="sm" alt="Deck AIStack logo" />
    <div>
      <strong>Deck AIStack</strong>
      <p>Product utilities</p>
    </div>
  </div>
  <div class="app-utilities__actions">
    <button type="button" class="app-utilities__status" class:app-utilities__status--offline={!$sessionState.user && !$sessionState.inspection?.active}>
      <span class="app-utilities__status-dot"></span>
      {connectedLabel}
    </button>
    {#if $sessionState.inspection?.active}
      <span class="app-utilities__mode">Bypass active</span>
    {/if}
    <ThemeToggle />
    {#if $sessionState.user?.role === 'super_admin'}
      <a class="pill app-utilities__admin" href="/admin">Admin</a>
    {/if}
    <a class="pill app-utilities__billing" href="/app/billing">
      {$sessionState.billingPlan === 'pro' ? 'Pro Plan' : 'Free Plan'}
    </a>
    <button type="button" class="app-topbar__menu">
      <span class="app-avatar">{avatarLabel}</span>
      <span class="app-topbar__identity">
        <strong>{identityLabel}</strong>
        <small>{roleLabel}</small>
      </span>
    </button>
  </div>
</div>

<style>
  :global(.app-shell__footer-utilities) {
    width: min(100%, 22rem);
    justify-self: end;
    align-self: end;
    padding: 0 0.85rem 0.85rem 0;
  }

  :global(.app-shell__footer-utilities) :global(.app-utilities) {
    display: grid;
    gap: 0.72rem;
    justify-content: stretch;
    align-items: stretch;
    padding: 0.78rem;
    border: 1px solid var(--line);
    border-radius: 18px;
    background:
      radial-gradient(circle at top left, rgba(24, 200, 255, 0.1), transparent 34%),
      color-mix(in srgb, var(--surface) 92%, transparent);
    box-shadow: 0 18px 42px rgba(2, 8, 23, 0.22);
    backdrop-filter: blur(18px);
  }

  :global(.app-shell__footer-utilities) :global(.app-utilities__brand) {
    display: grid;
    grid-template-columns: 32px minmax(0, 1fr);
    gap: 0.65rem;
    align-items: center;
  }

  :global(.app-shell__footer-utilities) :global(.app-utilities__actions) {
    display: grid;
    gap: 0.5rem;
    align-items: stretch;
  }

  :global(.app-shell__footer-utilities) :global(.app-utilities__actions > *) {
    width: 100%;
    min-height: 38px;
    justify-content: flex-start;
  }

  :global(.app-shell__footer-utilities) :global(.app-topbar__menu) {
    display: grid;
    grid-template-columns: 32px minmax(0, 1fr);
    gap: 0.55rem;
    border-radius: 14px;
    padding: 0.28rem 0.42rem;
  }

  :global(.app-shell__footer-utilities) :global(.app-topbar__identity) {
    display: grid;
  }

  .app-utilities__mode {
    border-radius: 999px;
    border: 1px solid rgba(245, 158, 11, 0.32);
    background: rgba(245, 158, 11, 0.12);
    color: #fcd34d;
    padding: 0.45rem 0.75rem;
    font-size: 0.75rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .app-utilities__admin {
    border-color: rgba(125, 211, 252, 0.34);
    background: rgba(14, 165, 233, 0.12);
    color: #bae6fd;
  }

  .app-utilities__status--offline {
    border-color: rgba(248, 113, 113, 0.36);
    background: rgba(127, 29, 29, 0.18);
    color: #fecaca;
  }

  @media (max-width: 720px) {
    :global(.app-shell__footer-utilities) {
      width: 100%;
      justify-self: stretch;
      padding: 0 0.75rem 0.75rem;
    }
  }
</style>