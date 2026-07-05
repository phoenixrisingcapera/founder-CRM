<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const quotas = $derived(data.quotas);
  const summaryCards = $derived([
    { label: 'AI buckets', value: quotas.summary.aiUsageBucketCount, detail: `${quotas.summary.aiBucketsReturned} returned` },
    { label: 'Rate buckets', value: quotas.summary.rateLimitBucketCount, detail: `${quotas.summary.rateBucketsReturned} returned` },
    { label: 'Daily quota', value: quotas.summary.dailyAiGenerationQuota, detail: 'AI generations' },
    { label: 'Failures', value: quotas.recentFailures.length, detail: 'Recent security/audit failures' }
  ]);

  function label(value: string | null | undefined) {
    return value?.replaceAll('_', ' ').replaceAll(':', ' / ') ?? 'Unknown';
  }

  function formatDate(value: unknown) {
    if (!value || typeof value !== 'string') return 'n/a';
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(value));
  }

  function formatValue(value: unknown) {
    if (value === null || value === undefined || value === '') return 'n/a';
    if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(2);
    return String(value);
  }
</script>

<AppShell
  title="Quotas"
  subtitle="Read-only quota and rate-limit pressure across AI generation and guarded service flows."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="quotas-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/elements">Elements</a>
      <a href="/admin/failure-tickets">Failure tickets</a>
      <a href="/admin/users">Users</a>
      <a class="active" href="/admin/quotas">Quotas</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/provider-health">Provider health</a>
    </nav>

    <section class="summary-grid" aria-label="Quota summary">
      {#each summaryCards as card}
        <article class="panel summary-card">
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.detail}</small>
        </article>
      {/each}
    </section>

    <section class="table-grid">
      <article class="panel table-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">AI usage</p>
            <h2>Daily generation buckets</h2>
          </div>
          <a class="button secondary" href="/admin/quotas?limit=250">Load 250</a>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Quota</th>
                <th>Usage</th>
                <th>Remaining</th>
                <th>Pressure</th>
                <th>Window</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {#each quotas.aiUsageBuckets as bucket}
                <tr>
                  <td>{formatValue(bucket.userEmail ?? bucket.userId)}</td>
                  <td>{label(String(bucket.quotaKey ?? 'unknown'))}</td>
                  <td>{formatValue(bucket.usageCount)} / {formatValue(bucket.configuredLimit)}</td>
                  <td>{formatValue(bucket.remaining)}</td>
                  <td>{formatValue(typeof bucket.pressure === 'number' ? bucket.pressure * 100 : null)}%</td>
                  <td>{formatDate(bucket.windowStart)}</td>
                  <td>{formatDate(bucket.updatedAt)}</td>
                </tr>
              {:else}
                <tr><td colspan="7" class="empty">No AI usage buckets recorded.</td></tr>
              {/each}
            </tbody>
          </table>
        </div>
      </article>

      <article class="panel table-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Rate limits</p>
            <h2>Request buckets</h2>
          </div>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Actor key</th>
                <th>Requests</th>
                <th>Window</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {#each quotas.rateLimitBuckets as bucket}
                <tr>
                  <td>{formatValue(bucket.actorKey)}</td>
                  <td>{formatValue(bucket.requestCount)}</td>
                  <td>{formatDate(bucket.windowStart)}</td>
                  <td>{formatDate(bucket.updatedAt)}</td>
                </tr>
              {:else}
                <tr><td colspan="4" class="empty">No rate-limit buckets recorded.</td></tr>
              {/each}
            </tbody>
          </table>
        </div>
      </article>
    </section>

    <section class="panel failures-panel">
      <p class="eyebrow">Recent failures</p>
      <h2>Quota-adjacent audit events</h2>
      <div class="failure-list">
        {#each quotas.recentFailures as failure}
          <div class="failure-row">
            <strong>{formatValue(failure.action)}</strong>
            <span>{formatValue(failure.actorEmail ?? failure.actorUserId ?? 'system')}</span>
            <small>{formatValue(failure.resourceType)} · {formatValue(failure.requestId)} · {formatDate(failure.createdAt)}</small>
          </div>
        {:else}
          <p class="muted">No recent quota or provider configuration failures.</p>
        {/each}
      </div>
    </section>

    <section class="panel redaction-panel">
      <div>
        <p class="eyebrow">Redaction</p>
        <h2>Safe admin view</h2>
        <p>{quotas.redaction.detailPolicy}</p>
      </div>
      <div class="redacted-list" aria-label="Redacted fields">
        {#each quotas.redaction.sensitiveFieldsRedacted as field}
          <span>{field}</span>
        {/each}
      </div>
    </section>
  </section>
</AppShell>

<style>
  .quotas-page,
  .table-grid,
  .failure-list {
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
  .table-panel,
  .failures-panel,
  .redaction-panel {
    padding: 1rem;
  }

  .summary-card {
    display: grid;
    gap: 0.35rem;
  }

  .summary-card span,
  .summary-card small {
    color: var(--text-muted);
  }

  .summary-card strong {
    font-size: 1.5rem;
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
  .failures-panel h2,
  .failures-panel p,
  .redaction-panel h2,
  .redaction-panel p {
    margin: 0;
  }

  .table-scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    min-width: 760px;
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

  .empty {
    color: var(--text-muted);
    text-align: center;
  }

  .failure-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(180px, 0.5fr);
    gap: 0.2rem 1rem;
    border-top: 1px solid var(--border);
    padding-top: 0.65rem;
  }

  .failure-row span,
  .failure-row small {
    color: var(--text-muted);
  }

  .failure-row small {
    grid-column: 1 / -1;
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

  .redacted-list span {
    display: inline-flex;
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.22rem 0.5rem;
    color: var(--text-muted);
    white-space: nowrap;
  }

  @media (max-width: 900px) {
    .redaction-panel,
    .failure-row {
      grid-template-columns: 1fr;
    }
  }
</style>
