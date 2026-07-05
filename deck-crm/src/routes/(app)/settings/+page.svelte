<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import PageHeader from '$components/PageHeader.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const inspectionRoutes = $derived.by(() => {
    const activeDeckId = data.workspace.activeDeckId;

    return [
      '/welcome',
      '/dashboard',
      '/decks',
      '/decks/new',
      '/templates',
      '/insights',
      '/exports',
      '/datasets',
      '/team',
      '/app/billing',
      '/settings',
      '/settings/account/settings',
      '/settings/account/connected-accounts',
      activeDeckId ? `/decks/${activeDeckId}/smart-deck` : null,
      activeDeckId ? `/admin/slides/${activeDeckId}` : null,
      activeDeckId ? `/decks/${activeDeckId}/due-diligence` : null,
      activeDeckId ? `/decks/${activeDeckId}/export` : null,
      activeDeckId ? `/admin/processing/${activeDeckId}` : null
    ].filter(Boolean) as string[];
  });
</script>

<AppShell
  title="Settings"
  subtitle="Account and workspace controls remain available even before the first deck is uploaded."
  activeNav="settings"
  deckLabel={data.workspace.workspace.name}
>
  <section class="section-stack app-content-narrow">
    <PageHeader
      eyebrow="Settings"
      title="Account, workspace, and connection controls"
      subtitle="Use settings to manage your profile, optional connected accounts, and workspace-level preferences."
      aside={`Decks in workspace: ${data.workspace.deckCount}`}
    />

    <section class="settings-grid">
      <article class="panel settings-card">
        <div class="eyebrow">Account</div>
        <h3>{data.settings.user.name}</h3>
        <p class="muted">{data.settings.user.email}</p>
        <a class="button secondary" href="/settings/account/settings">Open account settings</a>
      </article>

      <article class="panel settings-card">
        <div class="eyebrow">Connected accounts</div>
        <h3>{data.settings.connectedAccounts.length} configured</h3>
        <p class="muted">LinkedIn and Microsoft remain optional infrastructure that can enrich future agent context.</p>
        <a class="button secondary" href="/settings/account/connected-accounts">Manage connections</a>
      </article>
    </section>

    {#if data.inspection?.active}
      <section class="inspection-grid">
        <article class="panel inspection-card">
          <div class="eyebrow">Founder inspection mode</div>
          <h3>Preview bypass is active</h3>
          <p class="muted">
            Route access is open for the founder session even if billing, provider setup, or some service slices are not finished.
          </p>
          <dl class="inspection-meta">
            <div><dt>Service API</dt><dd>{data.inspection.backendConfigured ? 'Configured' : 'Not configured'}</dd></div>
            <div><dt>Route access bypass</dt><dd>{data.inspection.bypasses.routeAccess ? 'Enabled' : 'Disabled'}</dd></div>
            <div><dt>Billing bypass</dt><dd>{data.inspection.bypasses.billing ? 'Enabled' : 'Disabled'}</dd></div>
            <div><dt>Provider bypass</dt><dd>{data.inspection.bypasses.providers ? 'Enabled' : 'Disabled'}</dd></div>
          </dl>
        </article>

        <article class="panel inspection-card">
          <div class="eyebrow">Route inspection</div>
          <h3>Direct links for preview debugging</h3>
          <div class="route-list">
            {#each inspectionRoutes as route}
              <a class="route-pill" href={route}>{route}</a>
            {/each}
          </div>
        </article>
      </section>
    {/if}
  </section>
</AppShell>

<style>
  .settings-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }

  .settings-card {
    padding: 1.2rem;
    display: grid;
    gap: 0.8rem;
  }

  .inspection-grid {
    display: grid;
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
    gap: 1rem;
  }

  .inspection-card {
    padding: 1.2rem;
    display: grid;
    gap: 0.9rem;
  }

  .inspection-meta {
    display: grid;
    gap: 0.75rem;
    margin: 0;
  }

  .inspection-meta dt {
    color: var(--muted);
    font-size: 0.82rem;
  }

  .inspection-meta dd {
    margin: 0.15rem 0 0;
    font-weight: 600;
  }

  .route-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.7rem;
  }

  .route-pill {
    border-radius: 999px;
    border: 1px solid var(--line);
    padding: 0.6rem 0.85rem;
    background: rgba(255,255,255,0.03);
    color: var(--ink-strong);
    font-size: 0.92rem;
  }

  h3 {
    margin: 0;
  }

  @media (max-width: 900px) {
    .settings-grid,
    .inspection-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
