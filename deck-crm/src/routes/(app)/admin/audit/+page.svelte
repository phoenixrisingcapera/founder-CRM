<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const audit = $derived(data.audit);
  const actionOptions = $derived(audit.topActions.map((item) => item.action));
  const resultOptions = $derived(Object.keys(audit.resultCounts).sort((a, b) => a.localeCompare(b)));
  const resourceOptions = $derived(Object.keys(audit.resourceTypeCounts).sort((a, b) => a.localeCompare(b)));

  const summaryCards = $derived([
    { label: 'Returned', value: audit.events.length, detail: `${audit.total} matching events` },
    { label: 'Actions', value: audit.topActions.length, detail: 'Top action groups' },
    { label: 'Results', value: Object.keys(audit.resultCounts).length, detail: 'Distinct result states' },
    { label: 'Resources', value: Object.keys(audit.resourceTypeCounts).length, detail: 'Resource types' }
  ]);

  function label(value: string | null | undefined) {
    return value?.replaceAll('_', ' ').replaceAll(':', ' / ') ?? 'Unknown';
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
    const normalized = status.toLowerCase();
    if (['failure', 'failed', 'error', 'denied'].includes(normalized)) return 'failed';
    if (['pending', 'running'].includes(normalized)) return 'running';
    if (['success', 'allowed', 'completed'].includes(normalized)) return 'completed';
    return 'neutral';
  }
</script>

<AppShell
  title="Audit"
  subtitle="Read-only security audit event feed with safe summaries and bounded filters."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="audit-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/elements">Elements</a>
      <a class="active" href="/admin/audit">Audit</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
    </nav>

    <section class="summary-grid" aria-label="Audit summary">
      {#each summaryCards as card}
        <article class="panel summary-card">
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.detail}</small>
        </article>
      {/each}
    </section>

    <form class="panel filters" method="GET" aria-label="Audit filters">
      <label>
        Action
        <select name="action" value={audit.filters.action ?? ''}>
          <option value="">All actions</option>
          {#each actionOptions as item}
            <option value={item}>{label(item)}</option>
          {/each}
        </select>
      </label>
      <label>
        Result
        <select name="result" value={audit.filters.result ?? ''}>
          <option value="">All results</option>
          {#each resultOptions as item}
            <option value={item}>{label(item)}</option>
          {/each}
        </select>
      </label>
      <label>
        Resource
        <select name="resourceType" value={audit.filters.resourceType ?? ''}>
          <option value="">All resources</option>
          {#each resourceOptions as item}
            <option value={item === 'none' ? '' : item}>{label(item)}</option>
          {/each}
        </select>
      </label>
      <label>
        Actor
        <input name="actor" type="search" value={audit.filters.actor ?? ''} placeholder="email or user id" />
      </label>
      <input type="hidden" name="limit" value={audit.limit} />
      <button class="button" type="submit">Apply</button>
      <a class="button secondary" href="/admin/audit">Reset</a>
      <a class="button secondary" href="/admin/audit?limit=250">Load 250</a>
    </form>

    <section class="audit-layout">
      <article class="panel table-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Events</p>
            <h2>{audit.events.length} of {audit.total} events</h2>
          </div>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Created</th>
                <th>Action</th>
                <th>Result</th>
                <th>Actor</th>
                <th>Resource</th>
                <th>Request</th>
                <th>Detail keys</th>
              </tr>
            </thead>
            <tbody>
              {#each audit.events as event}
                <tr>
                  <td>{formatDate(event.createdAt)}</td>
                  <td>{label(event.action)}</td>
                  <td><span class={`status ${statusTone(event.result)}`}>{label(event.result)}</span></td>
                  <td>{event.actorEmail ?? event.actorUserId ?? 'system'}</td>
                  <td>{event.resourceType ?? 'n/a'}<br /><small>{event.resourceId ?? 'n/a'}</small></td>
                  <td>{event.requestId ?? 'n/a'}</td>
                  <td>{event.detailKeys.join(', ') || 'n/a'}</td>
                </tr>
              {:else}
                <tr><td colspan="7" class="empty">No audit events match the current filters.</td></tr>
              {/each}
            </tbody>
          </table>
        </div>
      </article>

      <aside class="panel side-panel">
        <p class="eyebrow">Top actions</p>
        <h2>Distribution</h2>
        <div class="count-list">
          {#each audit.topActions as item}
            <div>
              <span>{label(item.action)}</span>
              <strong>{item.count}</strong>
            </div>
          {:else}
            <p class="muted">No action counts recorded.</p>
          {/each}
        </div>
      </aside>
    </section>

    <section class="panel redaction-panel">
      <div>
        <p class="eyebrow">Redaction</p>
        <h2>Safe admin view</h2>
        <p>{audit.redaction.detailPolicy}</p>
      </div>
      <div class="redacted-list" aria-label="Redacted fields">
        {#each audit.redaction.sensitiveFieldsRedacted as field}
          <span>{field}</span>
        {/each}
      </div>
    </section>
  </section>
</AppShell>

<style>
  .audit-page,
  .audit-layout,
  .count-list {
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
  .side-panel,
  .redaction-panel {
    padding: 1rem;
  }

  .summary-card {
    display: grid;
    gap: 0.35rem;
  }

  .summary-card span,
  .summary-card small,
  td small,
  .count-list span {
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

  .audit-layout {
    grid-template-columns: minmax(0, 1fr) minmax(240px, 320px);
    align-items: start;
  }

  .panel-head,
  .redaction-panel {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
  }

  .panel-head h2,
  .panel-head p,
  .side-panel h2,
  .side-panel p,
  .redaction-panel h2,
  .redaction-panel p {
    margin: 0;
  }

  .table-scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    min-width: 940px;
    border-collapse: collapse;
    font-size: 0.82rem;
  }

  th,
  td {
    border-top: 1px solid var(--border);
    padding: 0.55rem 0.5rem;
    text-align: left;
    vertical-align: top;
  }

  th {
    color: var(--text-muted);
    font-weight: 600;
  }

  .status,
  .redacted-list span {
    display: inline-flex;
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.22rem 0.5rem;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .status.failed {
    border-color: color-mix(in srgb, var(--danger) 45%, transparent);
    color: var(--danger);
  }

  .status.running {
    border-color: color-mix(in srgb, var(--accent) 45%, transparent);
    color: var(--accent);
  }

  .status.completed {
    border-color: color-mix(in srgb, var(--success) 45%, transparent);
    color: var(--success);
  }

  .count-list div {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.25rem 0.75rem;
    border-top: 1px solid var(--border);
    padding-top: 0.65rem;
  }

  .empty {
    color: var(--text-muted);
    text-align: center;
  }

  .redaction-panel {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(280px, 0.8fr);
  }

  .redacted-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  @media (max-width: 980px) {
    .audit-layout,
    .redaction-panel {
      grid-template-columns: 1fr;
    }
  }
</style>
