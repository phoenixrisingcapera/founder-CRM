<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import WelcomeActionCard from '$components/WelcomeActionCard.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const summaryCards = $derived([
    { label: 'Agent runs', value: data.overview.summary.agentRuns, detail: `${data.overview.summary.agentRunsRunning} running` },
    { label: 'Failed runs', value: data.overview.summary.agentRunsFailed, detail: 'Needs inspection' },
    { label: 'Decks', value: data.overview.summary.decks, detail: `${data.overview.summary.workspaces} workspaces` },
    { label: 'Audit events', value: data.overview.summary.auditEvents, detail: `${data.overview.summary.authSessions} auth sessions` },
    { label: 'AI configured', value: data.overview.summary.workspaceAiConfigured, detail: 'Workspace provider settings' },
    { label: 'Quota buckets', value: data.overview.summary.aiUsageBuckets, detail: `${data.overview.summary.rateLimitBuckets} rate buckets` }
  ]);
</script>

<AppShell
  title="Admin"
  subtitle="Read-only operational overview for agent workflows, audit activity, quotas, and provider state."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="admin-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a class="active" href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/elements">Elements</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/failure-tickets">Failure tickets</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/testers">Testers</a>
      <a href="/admin/users">Users</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
      <a href="/admin/deployment-readiness">Deployment readiness</a>
    </nav>

    <section class="admin-grid" aria-label="Admin summary">
      {#each summaryCards as card}
        <article class="panel admin-card">
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.detail}</small>
        </article>
      {/each}
    </section>

    <section class="admin-staging" aria-label="Temporarily staged workspace actions">
      <WelcomeActionCard
        title="Add supporting notes"
        message="Add audience, purpose, company, founder, and team notes to support a URL, logo, or slide miniature source."
        href="/decks/new?firstBatch=supporting_context"
        ctaLabel="Add notes"
        icon="☷"
        meta="Admin staged"
      />
    </section>

    <section class="admin-columns">
      <article class="panel admin-panel">
        <div class="admin-panel__head">
          <div>
            <p class="eyebrow">Recent agent runs</p>
            <h2>Operational feed</h2>
          </div>
          <a class="button secondary" href="/admin/agents">Open all</a>
        </div>
        <div class="admin-run-list">
          {#each data.overview.recentRuns as run}
            <a class="admin-run-row" href={`/admin/agents/${encodeURIComponent(run.id)}`}>
              <span class={`admin-status ${run.status.toLowerCase()}`}>{run.status}</span>
              <strong>{run.runType.replaceAll('_', ' ')}</strong>
              <small>{run.deckTitle ?? run.deckId ?? 'No deck context'} · {run.provider ?? 'provider unknown'}</small>
            </a>
          {:else}
            <p class="muted">No agent runs have been recorded yet.</p>
          {/each}
        </div>
      </article>

      <article class="panel admin-panel">
        <div class="admin-panel__head">
          <div>
            <p class="eyebrow">Recent activity</p>
            <h2>Audit trail</h2>
          </div>
        </div>
        <div class="admin-run-list">
          {#each data.overview.recentActivity as event}
            <div class="admin-run-row">
              <span class={`admin-status ${event.result.toLowerCase()}`}>{event.result}</span>
              <strong>{event.action}</strong>
              <small>{event.actorEmail ?? event.actorUserId ?? 'system'} · {event.requestId ?? 'no request id'}</small>
            </div>
          {:else}
            <p class="muted">No audit events have been recorded yet.</p>
          {/each}
        </div>
      </article>
    </section>
  </section>
</AppShell>

<style>
  .admin-page {
    display: grid;
    gap: 1rem;
  }

  .admin-tabs {
    display: flex;
    gap: 0.5rem;
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

  .admin-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 0.85rem;
  }

  .admin-staging {
    display: grid;
    grid-template-columns: minmax(240px, 320px);
    gap: 1rem;
  }

  .admin-card,
  .admin-panel {
    padding: 1rem;
  }

  .admin-card {
    display: grid;
    gap: 0.4rem;
  }

  .admin-card span,
  .admin-card small,
  .admin-run-row small {
    color: var(--text-muted);
  }

  .admin-card strong {
    font-size: 1.8rem;
  }

  .admin-columns {
    display: grid;
    grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.8fr);
    gap: 1rem;
  }

  .admin-panel__head {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
    margin-bottom: 1rem;
  }

  .admin-panel h2,
  .admin-panel p {
    margin: 0;
  }

  .admin-run-list {
    display: grid;
    gap: 0.6rem;
  }

  .admin-run-row {
    display: grid;
    grid-template-columns: 110px minmax(0, 1fr);
    gap: 0.35rem 0.8rem;
    align-items: center;
    border-top: 1px solid var(--border);
    padding-top: 0.6rem;
    color: inherit;
    text-decoration: none;
  }

  .admin-run-row small {
    grid-column: 2;
  }

  .admin-status {
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.25rem 0.5rem;
    text-align: center;
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .admin-status.failed,
  .admin-status.error,
  .admin-status.failure {
    border-color: rgba(248, 113, 113, 0.45);
    color: #fecaca;
  }

  .admin-status.running,
  .admin-status.queued,
  .admin-status.pending {
    border-color: rgba(250, 204, 21, 0.45);
    color: #fde68a;
  }

  .admin-status.completed,
  .admin-status.success,
  .admin-status.ready {
    border-color: rgba(52, 211, 153, 0.45);
    color: #bbf7d0;
  }

  @media (max-width: 900px) {
    .admin-columns {
      grid-template-columns: 1fr;
    }
  }
</style>
