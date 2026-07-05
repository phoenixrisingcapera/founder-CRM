<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const failureTickets = $derived(data.failureTickets);
  const statusOptions = ['new', 'acknowledged', 'investigating', 'fixed', 'ignored'];
  const severityOptions = ['critical', 'high', 'medium', 'low'];
  const sourceOptions = ['frontend', 'api', 'backend', 'loader', 'fallback'];

  const summaryCards = $derived([
    { label: 'Returned', value: failureTickets.tickets.length, detail: `${failureTickets.total} matching tickets` },
    { label: 'New', value: failureTickets.statusCounts.new ?? 0, detail: 'Needs triage' },
    { label: 'Critical', value: failureTickets.severityCounts.critical ?? 0, detail: 'Highest severity' },
    { label: 'Backend', value: failureTickets.sourceCounts.backend ?? 0, detail: 'Unhandled exceptions' }
  ]);

  function label(value: string | null | undefined) {
    return value?.replaceAll('_', ' ') ?? 'Unknown';
  }

  function formatDate(value: string | null) {
    if (!value) return 'n/a';
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(value));
  }

  function statusTone(status: string) {
    if (status === 'new') return 'failed';
    if (status === 'investigating') return 'running';
    if (status === 'fixed') return 'completed';
    if (status === 'ignored') return 'neutral';
    return 'pending';
  }

  function severityTone(severity: string) {
    if (['critical', 'high'].includes(severity)) return 'failed';
    if (severity === 'medium') return 'running';
    return 'neutral';
  }
</script>

<AppShell
  title="Failure tickets"
  subtitle="Production page, API, loader, and backend failures captured for admin review."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="tickets-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/elements">Elements</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/users">Users</a>
      <a class="active" href="/admin/failure-tickets">Failure tickets</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
    </nav>

    <section class="summary-grid" aria-label="Failure ticket summary">
      {#each summaryCards as card}
        <article class="panel summary-card">
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.detail}</small>
        </article>
      {/each}
    </section>

    <form class="panel filters" method="GET" aria-label="Failure ticket filters">
      <label>
        Status
        <select name="status" value={failureTickets.filters.status ?? ''}>
          <option value="">All statuses</option>
          {#each statusOptions as item}
            <option value={item}>{label(item)}</option>
          {/each}
        </select>
      </label>
      <label>
        Severity
        <select name="severity" value={failureTickets.filters.severity ?? ''}>
          <option value="">All severities</option>
          {#each severityOptions as item}
            <option value={item}>{label(item)}</option>
          {/each}
        </select>
      </label>
      <label>
        Source
        <select name="source" value={failureTickets.filters.source ?? ''}>
          <option value="">All sources</option>
          {#each sourceOptions as item}
            <option value={item}>{label(item)}</option>
          {/each}
        </select>
      </label>
      <label>
        Deck
        <input name="deckId" type="search" value={failureTickets.filters.deckId ?? ''} placeholder="deck id" />
      </label>
      <input type="hidden" name="limit" value={failureTickets.limit} />
      <button class="button" type="submit">Apply</button>
      <a class="button secondary" href="/admin/failure-tickets">Reset</a>
      <a class="button secondary" href="/admin/failure-tickets?limit=250">Load 250</a>
    </form>

    <article class="panel table-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Tickets</p>
          <h2>{failureTickets.tickets.length} of {failureTickets.total} tickets</h2>
        </div>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Created</th>
              <th>Status</th>
              <th>Severity</th>
              <th>Source</th>
              <th>Location</th>
              <th>Error</th>
              <th>User</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {#each failureTickets.tickets as ticket}
              <tr>
                <td>{formatDate(ticket.createdAt)}</td>
                <td><span class={`status ${statusTone(ticket.status)}`}>{label(ticket.status)}</span></td>
                <td><span class={`status ${severityTone(ticket.severity)}`}>{label(ticket.severity)}</span></td>
                <td>{label(ticket.source)}</td>
                <td>{ticket.route ?? ticket.apiPath ?? 'n/a'}<br /><small>{ticket.statusCode ?? 'no status'}</small></td>
                <td>{ticket.errorName ?? 'Error'}<br /><small>{ticket.errorMessage ?? 'No message captured'}</small></td>
                <td>{ticket.userEmail ?? ticket.userId ?? 'anonymous'}<br /><small>{ticket.deckId ?? 'no deck'}</small></td>
                <td><a class="button secondary" href={`/admin/failure-tickets/${encodeURIComponent(ticket.id)}`}>Open</a></td>
              </tr>
            {:else}
              <tr><td colspan="8" class="empty">No failure tickets match the current filters.</td></tr>
            {/each}
          </tbody>
        </table>
      </div>
    </article>

    <section class="panel redaction-panel">
      <div>
        <p class="eyebrow">Redaction</p>
        <h2>Safe admin view</h2>
        <p>{failureTickets.redaction.detailPolicy}</p>
      </div>
      <div class="redacted-list" aria-label="Redacted fields">
        {#each failureTickets.redaction.sensitiveFieldsRedacted as field}
          <span>{field}</span>
        {/each}
      </div>
    </section>
  </section>
</AppShell>

<style>
  .tickets-page {
    display: grid;
    gap: 1rem;
  }

  .admin-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
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
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.75rem;
  }

  .summary-card,
  .filters,
  .table-panel,
  .redaction-panel {
    padding: 1rem;
  }

  .summary-card {
    display: grid;
    gap: 0.35rem;
  }

  .summary-card span,
  .summary-card small,
  td small {
    color: var(--text-muted);
  }

  .summary-card strong {
    font-size: 1.5rem;
  }

  .filters {
    display: flex;
    flex-wrap: wrap;
    align-items: end;
    gap: 0.65rem;
  }

  .filters label {
    display: grid;
    gap: 0.35rem;
    min-width: 150px;
    color: var(--text-muted);
    font-size: 0.78rem;
  }

  .filters select,
  .filters input {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    color: var(--text);
    padding: 0.55rem 0.65rem;
  }

  .table-scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    min-width: 980px;
  }

  th,
  td {
    padding: 0.75rem;
    border-bottom: 1px solid var(--border);
    text-align: left;
    vertical-align: top;
  }

  .status {
    display: inline-flex;
    border-radius: 999px;
    padding: 0.25rem 0.5rem;
    background: var(--surface-subtle);
    color: var(--text-muted);
  }

  .status.failed {
    background: color-mix(in srgb, #ef4444 14%, transparent);
    color: #ef4444;
  }

  .status.running {
    background: color-mix(in srgb, #f59e0b 14%, transparent);
    color: #b45309;
  }

  .status.completed {
    background: color-mix(in srgb, #10b981 14%, transparent);
    color: #047857;
  }

  .redaction-panel {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
  }

  .redacted-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .redacted-list span {
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.35rem 0.55rem;
    color: var(--text-muted);
  }
</style>
