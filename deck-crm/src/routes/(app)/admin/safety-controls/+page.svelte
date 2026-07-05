<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const controls = $derived(data.controls);
  const summaryCards = $derived([
    { label: 'Backlog', value: controls.summary.incidentBacklogTotal, detail: `${controls.summary.incidentBacklogNew} new` },
    { label: 'Critical', value: controls.summary.incidentBacklogCritical, detail: 'Needs immediate triage' },
    {
      label: 'Guardrails',
      value: controls.summary.guardrailsConfigured ? 'configured' : 'unconfigured',
      detail: `Service ${controls.summary.guardrailStatus ?? 'unknown'}`
    },
    {
      label: 'Super admin',
      value: controls.summary.superAdminConfigured ? 'connected' : 'unconfigured',
      detail: `Control plane ${controls.summary.superAdminStatus ?? 'unknown'}`
    },
    { label: 'Evaluations', value: controls.summary.guardrailEvaluations, detail: 'Last 25 + audit tail' },
    { label: 'Blocked by guardrails', value: controls.summary.guardrailBlockedTickets, detail: 'In safety backlog' }
  ]);

  const allowedCount = $derived(controls.guardrailDecisions.counts.allowed);
  const blockedCount = $derived(controls.guardrailDecisions.counts.blocked);
  const failedCount = $derived(controls.guardrailDecisions.counts.failed);

  function formatDate(value: string | null | undefined) {
    if (!value) return 'n/a';
    return new Intl.DateTimeFormat('en', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(
      new Date(value)
    );
  }

  function statusTone(value: string) {
    if (value === 'failed') return 'failed';
    if (value === 'blocked') return 'pending';
    return 'completed';
  }

  function label(value: string | null | undefined) {
    return value?.replaceAll('_', ' ') ?? 'unknown';
  }
</script>

<AppShell
  title="Safety controls"
  subtitle="Guardrail health, policy snapshots, and incident backlog for super-admin operations."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="safety-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/elements">Elements</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/failure-tickets">Failure tickets</a>
      <a href="/admin/users">Users</a>
      <a class="active" href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
    </nav>

    <section class="summary-grid" aria-label="Safety summary">
      {#each summaryCards as card}
        <article class="panel summary-card">
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.detail}</small>
        </article>
      {/each}
    </section>

    <section class="ops-grid">
      <article class="panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Guardrail service</p>
            <h2>{controls.guardrails.configured ? 'Connected' : 'Not connected'}</h2>
          </div>
          <span class={`status ${controls.guardrails.configured ? 'completed' : 'failed'}`}>
            {controls.guardrails.status}
          </span>
        </div>
        <dl>
          <div><dt>API</dt><dd>{controls.guardrails.baseUrl ?? 'Not configured'}</dd></div>
          <div><dt>Error</dt><dd>{controls.guardrails.error ?? 'none'}</dd></div>
          <div><dt>Evaluations</dt><dd>{allowedCount} allowed · {blockedCount} blocked · {failedCount} failed</dd></div>
          <div><dt>Policy</dt><dd>{controls.guardrails.policyRegistry?.activePolicy ?? 'not available'}</dd></div>
        </dl>
      </article>

      <article class="panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Super-admin service</p>
            <h2>{controls.superAdminService.configured ? 'Connected' : 'Not connected'}</h2>
          </div>
          <a class={`status ${controls.superAdminService.configured ? 'completed' : 'failed'}`} href={controls.superAdminService.baseUrl ?? '/admin/safety-controls'}>
            {controls.superAdminService.status}
          </a>
        </div>
        <dl>
          <div><dt>URL</dt><dd>{controls.superAdminService.baseUrl ?? 'Not configured'}</dd></div>
          <div><dt>Error</dt><dd>{controls.superAdminService.error ?? 'none'}</dd></div>
          <div><dt>Health</dt><dd>{controls.superAdminService.health?.status ?? 'unknown'}</dd></div>
        </dl>
      </article>

      <article class="panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Incident backlog</p>
            <h2>Recent tickets</h2>
          </div>
          <a class="button secondary" href="/admin/failure-tickets?status=new">Open new tickets</a>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Created</th>
                <th>Severity</th>
                <th>Source</th>
                <th>Route</th>
                <th>Error</th>
                <th>Open</th>
              </tr>
            </thead>
            <tbody>
              {#each controls.incidentBacklog.tickets as ticket}
                <tr>
                  <td>{formatDate(ticket.createdAt)}</td>
                  <td>{label(ticket.severity)}</td>
                  <td>{label(ticket.source)}</td>
                  <td>{ticket.route ?? ticket.apiPath ?? 'n/a'}</td>
                  <td>{ticket.errorName ?? 'Error'}</td>
                  <td><a class="button secondary" href={`/admin/failure-tickets/${encodeURIComponent(ticket.id)}`}>Open</a></td>
                </tr>
              {:else}
                <tr><td colspan="6" class="empty">No active incidents.</td></tr>
              {/each}
            </tbody>
          </table>
        </div>
      </article>
    </section>

    <article class="panel table-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Guardrail decisions</p>
          <h2>Live audit tail</h2>
        </div>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Decision</th>
              <th>Risk</th>
              <th>Policy</th>
              <th>Reason</th>
              <th>Actor</th>
            </tr>
          </thead>
          <tbody>
            {#each controls.guardrailDecisions.events as event}
              <tr>
                <td>{formatDate(event.createdAt)}</td>
                <td><span class={`status ${statusTone(event.result)}`}>{label(event.result)}</span></td>
                <td>{event.riskLevel ?? 'n/a'}</td>
                <td>{event.policy ?? 'n/a'}</td>
                <td>{event.reason ?? 'no reason'}</td>
                <td>{event.actorEmail ?? 'system'}</td>
              </tr>
            {:else}
              <tr><td colspan="6" class="empty">No guardrail audit events in this window.</td></tr>
            {/each}
          </tbody>
        </table>
      </div>
    </article>

    <section class="panel redaction-panel">
      <p>{controls.redaction.detailPolicy}</p>
    </section>
  </section>
</AppShell>

<style>
  .safety-page {
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
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.75rem;
  }

  .summary-card,
  .panel,
  .redaction-panel {
    padding: 1rem;
  }

  .summary-card {
    display: grid;
    gap: 0.35rem;
  }

  .summary-card span,
  .summary-card small,
  dd,
  dt,
  .redaction-panel {
    color: var(--text-muted);
  }

  .summary-card strong {
    font-size: 1.5rem;
  }

  .ops-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1rem;
  }

  .panel-head {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.8rem;
    align-items: start;
  }

  .panel h2,
  .panel p {
    margin: 0;
  }

  dl {
    display: grid;
    gap: 0.5rem;
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
  }

  .table-scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    min-width: 760px;
  }

  th,
  td {
    padding: 0.65rem 0.4rem;
    border-bottom: 1px solid var(--border);
    text-align: left;
    vertical-align: top;
  }

  .empty {
    color: var(--text-muted);
  }
</style>
