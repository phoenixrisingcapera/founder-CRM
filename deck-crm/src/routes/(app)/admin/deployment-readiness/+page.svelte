<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const readiness = $derived(data.readiness);
  const summaryCards = $derived([
    { label: 'Ready for tester traffic', value: readiness.summary.readyForTesterTraffic ? 'yes' : 'no', detail: 'API + worker split is healthy enough for tests' },
    { label: 'Hard checks', value: readiness.summary.hardOk ? 'pass' : 'fail', detail: `${readiness.summary.failedCount} failed` },
    { label: 'Warnings', value: readiness.summary.warningCount, detail: 'Non-blocking concerns' },
    { label: 'Environment', value: readiness.environment, detail: 'Backend runtime env' },
    { label: 'Service role', value: readiness.serviceRole, detail: 'Current Railway process' },
    { label: 'Checked at', value: new Intl.DateTimeFormat('en', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(readiness.checkedAt)), detail: 'Backend snapshot time' }
  ]);

  const orderedChecks = $derived(
    Object.entries(readiness.checks).sort(([left], [right]) => left.localeCompare(right))
  );

  function tone(status: string) {
    if (status === 'ok') return 'completed';
    if (status === 'warning') return 'running';
    return 'failed';
  }

  function label(value: string | null | undefined) {
    return value?.replaceAll('_', ' ').replaceAll(':', ' / ') ?? 'Unknown';
  }
</script>

<AppShell
  title="Deployment Readiness"
  subtitle="Backend deployment checks for API and worker split, database, storage, auth, and AI provider configuration."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="readiness-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/elements">Elements</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/testers">Testers</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
      <a class="active" href="/admin/deployment-readiness">Deployment readiness</a>
    </nav>

    <section class="summary-grid" aria-label="Deployment readiness summary">
      {#each summaryCards as card}
        <article class="panel summary-card">
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.detail}</small>
        </article>
      {/each}
    </section>

    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Service split</p>
          <h2>API vs worker</h2>
        </div>
        <a class="button secondary" href="/decks/new?firstBatch=slide_miniatures">Back to app</a>
      </div>
      <p class="muted">
        The API service should answer HTTP routes. The worker service should process jobs. If the API is failing, fix the API service first; if readiness is degraded because the queue is backed up, check the worker service separately.
      </p>
    </section>

    <section class="checks-grid">
      <article class="panel checks-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Checks</p>
            <h2>{orderedChecks.length} checks</h2>
          </div>
        </div>
        <div class="check-list">
          {#each orderedChecks as [key, check]}
            <article class={`check-row ${tone(check.status)}`}>
              <div>
                <strong>{label(key)}</strong>
                <p>{check.message}</p>
              </div>
              <div class="check-meta">
                <span class={`status ${tone(check.status)}`}>{check.status}</span>
                <small>{check.ok ? 'ok' : 'needs attention'}</small>
              </div>
            </article>
          {/each}
        </div>
      </article>

      <aside class="panel">
        <p class="eyebrow">Next step</p>
        <h2>{readiness.summary.readyForTesterTraffic ? 'Tester traffic is allowed' : 'Do not trust tester traffic yet'}</h2>
        <p class="muted">
          {#if readiness.summary.readyForTesterTraffic}
            The backend readiness service says the API, storage, and queue checks are acceptable for testers.
          {:else}
            One or more hard checks failed. Fix the failed check first, then re-run the deployment readiness page.
          {/if}
        </p>
        <div class="status-list">
          <div><span>Hard ok</span><strong>{readiness.summary.hardOk ? 'yes' : 'no'}</strong></div>
          <div><span>Failed</span><strong>{readiness.summary.failedCount}</strong></div>
          <div><span>Warnings</span><strong>{readiness.summary.warningCount}</strong></div>
        </div>
      </aside>
    </section>
  </section>
</AppShell>

<style>
  .readiness-page {
    display: grid;
    gap: 1rem;
  }

  .admin-tabs,
  .summary-grid,
  .checks-grid,
  .check-list,
  .status-list {
    display: grid;
    gap: 0.75rem;
  }

  .admin-tabs {
    display: flex;
    flex-wrap: wrap;
  }

  .admin-tabs a {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.55rem 0.75rem;
    color: var(--text-muted);
    text-decoration: none;
    background: var(--surface-subtle);
  }

  .admin-tabs a.active {
    color: var(--text);
    border-color: var(--accent);
  }

  .summary-grid {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }

  .summary-card,
  .checks-panel,
  .panel {
    padding: 1rem;
  }

  .summary-card {
    display: grid;
    gap: 0.35rem;
  }

  .summary-card span,
  .summary-card small,
  .muted,
  .check-row p,
  .status-list span,
  .status-list strong {
    color: var(--text-muted);
  }

  .summary-card strong {
    font-size: 1.7rem;
  }

  .checks-grid {
    grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
  }

  .panel-head {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
    margin-bottom: 1rem;
  }

  .panel h2,
  .panel p {
    margin: 0;
  }

  .check-list {
    gap: 0.65rem;
  }

  .check-row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    border-top: 1px solid var(--border);
    padding-top: 0.65rem;
  }

  .check-row:first-child {
    border-top: 0;
    padding-top: 0;
  }

  .check-row p {
    margin-top: 0.25rem;
  }

  .check-meta {
    display: grid;
    justify-items: end;
    gap: 0.25rem;
    text-align: right;
  }

  .status {
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.25rem 0.5rem;
    text-transform: capitalize;
  }

  .status.completed {
    color: #86efac;
  }

  .status.running {
    color: #fbbf24;
  }

  .status.failed {
    color: #fca5a5;
  }

  .status-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-top: 1rem;
  }

  .status-list div {
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.75rem;
    background: var(--surface-subtle);
    display: grid;
    gap: 0.2rem;
  }

  @media (max-width: 900px) {
    .checks-grid,
    .status-list {
      grid-template-columns: 1fr;
    }
  }
</style>
