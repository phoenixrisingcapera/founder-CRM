<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const health = $derived(data.providerHealth);
  let stateFilter = $state('all');
  let providerFilter = $state('all');

  const providers = $derived(uniqueOptions(health.workspaces.map((workspace) => String(workspace.provider ?? 'missing'))));
  const filteredWorkspaces = $derived(
    health.workspaces.filter((workspace) => {
      const provider = String(workspace.provider ?? 'missing');
      const state = workspace.isConfigured
        ? 'configured'
        : workspace.isSkipped
          ? 'skipped'
          : workspace.isRevoked
            ? 'revoked'
            : 'missing';
      return (
        (stateFilter === 'all' || state === stateFilter) &&
        (providerFilter === 'all' || provider === providerFilter)
      );
    })
  );

  const summaryCards = $derived([
    { label: 'Configured', value: health.summary.configured, detail: 'Active workspace credentials' },
    { label: 'Missing', value: health.summary.missing, detail: 'No active provider' },
    { label: 'Skipped', value: health.summary.skipped, detail: 'User skipped setup' },
    { label: 'Revoked', value: health.summary.revoked, detail: 'Credential revoked' },
    { label: 'System Claude', value: health.summary.systemAnthropicConfigured ? 'on' : 'off', detail: 'Fallback key configured' },
    { label: 'System OpenAI', value: health.summary.systemOpenAiConfigured ? 'on' : 'off', detail: 'Fallback key configured' },
    { label: 'Generation mode', value: health.summary.generationMode, detail: health.summary.mockMode ? 'Provider calls bypassed' : 'Provider calls active' },
    { label: 'Storage service', value: health.summary.uploadStorageBackend, detail: 'Generated artifacts' },
    { label: 'S3 bucket', value: health.summary.uploadStorageS3BucketConfigured ? 'set' : 'missing', detail: health.summary.uploadStorageS3Configured ? 'Bucket ready' : 'Check bucket config' },
    { label: 'S3 region', value: health.summary.uploadStorageS3RegionConfigured ? 'set' : 'missing', detail: 'Required for bucket access' }
  ]);

  function uniqueOptions(values: string[]) {
    return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b));
  }

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
    if (typeof value === 'boolean') return value ? 'yes' : 'no';
    return String(value);
  }

  function workspaceState(workspace: Record<string, unknown>) {
    if (workspace.isConfigured) return 'configured';
    if (workspace.isSkipped) return 'skipped';
    if (workspace.isRevoked) return 'revoked';
    return 'missing';
  }

  function stateTone(state: string) {
    if (state === 'configured') return 'completed';
    if (state === 'missing' || state === 'revoked') return 'failed';
    if (state === 'skipped') return 'running';
    return 'neutral';
  }
</script>

<AppShell
  title="Provider Health"
  subtitle="Read-only workspace AI provider configuration, credential state, and provider setup failures."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="provider-page">
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
      <a href="/admin/deployment-readiness">Deployment readiness</a>
      <a class="active" href="/admin/provider-health">Provider health</a>
    </nav>

    <section class="summary-grid" aria-label="Provider health summary">
      {#each summaryCards as card}
        <article class="panel summary-card">
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.detail}</small>
        </article>
      {/each}
    </section>

    <section class="filters" aria-label="Provider health filters">
      <label>
        State
        <select bind:value={stateFilter}>
          <option value="all">All states</option>
          <option value="configured">Configured</option>
          <option value="missing">Missing</option>
          <option value="skipped">Skipped</option>
          <option value="revoked">Revoked</option>
        </select>
      </label>
      <label>
        Provider
        <select bind:value={providerFilter}>
          <option value="all">All providers</option>
          {#each providers as provider}
            <option value={provider}>{label(provider)}</option>
          {/each}
        </select>
      </label>
      <a class="button secondary" href="/admin/provider-health?limit=250">Load 250</a>
    </section>

    <section class="table-grid">
      <article class="panel table-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Workspaces</p>
            <h2>{filteredWorkspaces.length} of {health.summary.workspacesReturned} returned</h2>
          </div>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Workspace</th>
                <th>Provider</th>
                <th>State</th>
                <th>Model</th>
                <th>Credential</th>
                <th>Use cases</th>
                <th>Configured</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {#each filteredWorkspaces as workspace}
                {@const state = workspaceState(workspace)}
                <tr>
                  <td>{formatValue(workspace.workspaceName)}<br /><small>{formatValue(workspace.ownerEmail ?? workspace.ownerUserId)}</small></td>
                  <td>{label(String(workspace.provider ?? 'missing'))}</td>
                  <td><span class={`status ${stateTone(state)}`}>{label(state)}</span></td>
                  <td>{formatValue(workspace.preferredModel)}</td>
                  <td>
                    {workspace.credentialLast4 ? `****${workspace.credentialLast4}` : 'n/a'}
                    <br /><small>{formatValue(workspace.keyVersion)}</small>
                  </td>
                  <td>
                    deck {formatValue(workspace.useForSmartDeck)} · edit {formatValue(workspace.useForSmartEdit)} · analysis {formatValue(workspace.useForAnalysis)}
                  </td>
                  <td>{formatDate(workspace.configuredAt ?? workspace.skippedAt ?? workspace.credentialRevokedAt)}</td>
                  <td>{formatDate(workspace.updatedAt)}</td>
                </tr>
              {:else}
                <tr><td colspan="8" class="empty">No workspaces match the current filters.</td></tr>
              {/each}
            </tbody>
          </table>
        </div>
      </article>

      <aside class="panel side-panel">
        <p class="eyebrow">Provider mix</p>
        <h2>Counts</h2>
        <div class="count-list">
          {#each Object.entries(health.providerCounts) as [provider, count]}
            <div>
              <span>{label(provider)}</span>
              <strong>{count}</strong>
            </div>
          {/each}
        </div>
      </aside>
    </section>

    <section class="panel failures-panel">
      <p class="eyebrow">Recent failures</p>
      <h2>Provider setup failures</h2>
      <div class="failure-list">
        {#each health.recentFailures as failure}
          <div class="failure-row">
            <strong>{formatValue(failure.action)}</strong>
            <span>{formatValue(failure.actorEmail ?? failure.actorUserId ?? 'system')}</span>
            <small>{formatValue(failure.resourceType)} · {formatValue(failure.requestId)} · {formatDate(failure.createdAt)}</small>
          </div>
        {:else}
          <p class="muted">No recent provider setup failures.</p>
        {/each}
      </div>
    </section>

    <section class="panel redaction-panel">
      <div>
        <p class="eyebrow">Redaction</p>
        <h2>Safe admin view</h2>
        <p>{health.redaction.detailPolicy}</p>
      </div>
      <div class="redacted-list" aria-label="Redacted fields">
        {#each health.redaction.sensitiveFieldsRedacted as field}
          <span>{field}</span>
        {/each}
      </div>
    </section>
  </section>
</AppShell>

<style>
  .provider-page,
  .table-grid,
  .failure-list,
  .count-list {
    display: grid;
    gap: 1rem;
  }

  .admin-tabs,
  .filters {
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
  .table-panel,
  .side-panel,
  .failures-panel,
  .redaction-panel {
    padding: 1rem;
  }

  .summary-card {
    display: grid;
    gap: 0.35rem;
  }

  .summary-card span,
  .summary-card small,
  .failure-row span,
  .failure-row small,
  td small {
    color: var(--text-muted);
  }

  .summary-card strong {
    font-size: 1.5rem;
  }

  .filters {
    align-items: end;
  }

  .filters label {
    display: grid;
    gap: 0.35rem;
    min-width: 150px;
    color: var(--text-muted);
    font-size: 0.78rem;
  }

  .filters select {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    color: var(--text);
    padding: 0.55rem 0.65rem;
  }

  .table-grid {
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
    min-width: 980px;
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

  .count-list div,
  .failure-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.25rem 0.75rem;
    border-top: 1px solid var(--border);
    padding-top: 0.65rem;
  }

  .failure-row small {
    grid-column: 1 / -1;
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
    .table-grid,
    .redaction-panel {
      grid-template-columns: 1fr;
    }
  }
</style>
