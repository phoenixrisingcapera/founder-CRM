<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { PageData } from './$types';

  let { data, form }: { data: PageData; form?: { message?: string } } = $props();

  const detail = $derived(data.failureTicket);
  const ticket = $derived(detail.ticket);
  const statusOptions = ['acknowledged', 'investigating', 'fixed', 'ignored'];

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

  function pretty(value: Record<string, unknown>) {
    return JSON.stringify(value, null, 2);
  }
</script>

<AppShell
  title="Failure ticket"
  subtitle={ticket.id}
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="ticket-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/elements">Elements</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/users">Users</a>
      <a href="/admin/failure-tickets">Failure tickets</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a class="active" href={`/admin/failure-tickets/${encodeURIComponent(ticket.id)}`}>Ticket detail</a>
    </nav>

    <section class="summary-grid" aria-label="Ticket summary">
      <article class="panel summary-card">
        <span>Status</span>
        <strong>{label(ticket.status)}</strong>
        <small>Updated {formatDate(ticket.updatedAt)}</small>
      </article>
      <article class="panel summary-card">
        <span>Severity</span>
        <strong>{label(ticket.severity)}</strong>
        <small>{label(ticket.source)} source</small>
      </article>
      <article class="panel summary-card">
        <span>Status code</span>
        <strong>{ticket.statusCode ?? 'n/a'}</strong>
        <small>{ticket.requestId ?? 'no request id'}</small>
      </article>
      <article class="panel summary-card">
        <span>User</span>
        <strong>{ticket.userEmail ?? 'anonymous'}</strong>
        <small>{ticket.deckId ?? 'no deck'}</small>
      </article>
    </section>

    <section class="detail-grid">
      <article class="panel detail-panel">
        <p class="eyebrow">Failure</p>
        <h2>{ticket.errorName ?? 'Error'}</h2>
        <p>{ticket.errorMessage ?? 'No message captured.'}</p>
        <dl>
          <div><dt>Route</dt><dd>{ticket.route ?? 'n/a'}</dd></div>
          <div><dt>Page URL</dt><dd>{ticket.pageUrl ?? 'n/a'}</dd></div>
          <div><dt>API path</dt><dd>{ticket.apiPath ?? 'n/a'}</dd></div>
          <div><dt>Created</dt><dd>{formatDate(ticket.createdAt)}</dd></div>
        </dl>
      </article>

      <form class="panel action-panel" method="POST" action="?/update">
        <p class="eyebrow">Admin action</p>
        <h2>Review state</h2>
        {#if form?.message}
          <p class="form-error">{form.message}</p>
        {/if}
        <label>
          Status
          <select name="status" value={ticket.status}>
            {#each statusOptions as item}
              <option value={item}>{label(item)}</option>
            {/each}
          </select>
        </label>
        <label>
          Notes
          <textarea name="adminNotes" rows="7" placeholder="Internal note for follow-up">{ticket.adminNotes ?? ''}</textarea>
        </label>
        <button class="button" type="submit">Save review</button>
      </form>
    </section>

    <details class="panel technical-panel">
      <summary>Technical context</summary>
      <div class="technical-grid">
        <section>
          <h3>Context JSON</h3>
          <pre>{pretty(ticket.context)}</pre>
        </section>
        <section>
          <h3>Stack trace</h3>
          <pre>{ticket.errorStack ?? 'No stack captured.'}</pre>
        </section>
      </div>
    </details>

    <section class="panel redaction-panel">
      <p>{detail.redaction.detailPolicy}</p>
    </section>
  </section>
</AppShell>

<style>
  .ticket-page,
  .detail-panel,
  .action-panel {
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

  .summary-grid,
  .detail-grid,
  .technical-grid {
    display: grid;
    gap: 1rem;
  }

  .summary-grid {
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  }

  .detail-grid {
    grid-template-columns: minmax(0, 1fr) minmax(280px, 0.45fr);
  }

  .summary-card,
  .detail-panel,
  .action-panel,
  .technical-panel,
  .redaction-panel {
    padding: 1rem;
  }

  .summary-card {
    display: grid;
    gap: 0.35rem;
  }

  .summary-card span,
  .summary-card small,
  dt,
  .redaction-panel {
    color: var(--text-muted);
  }

  .summary-card strong {
    font-size: 1.25rem;
  }

  dl {
    display: grid;
    gap: 0.65rem;
    margin: 0;
  }

  dl div {
    display: grid;
    gap: 0.2rem;
  }

  dt {
    font-size: 0.78rem;
  }

  dd {
    margin: 0;
    overflow-wrap: anywhere;
  }

  label {
    display: grid;
    gap: 0.35rem;
    color: var(--text-muted);
    font-size: 0.78rem;
  }

  select,
  textarea {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    color: var(--text);
    padding: 0.65rem;
  }

  .technical-panel summary {
    cursor: pointer;
    font-weight: 700;
  }

  pre {
    max-height: 28rem;
    overflow: auto;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem;
    background: var(--surface-subtle);
    color: var(--text);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .form-error {
    color: #ef4444;
  }

  @media (max-width: 860px) {
    .detail-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
