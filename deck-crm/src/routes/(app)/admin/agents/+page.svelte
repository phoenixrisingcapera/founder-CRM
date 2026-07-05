<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { AdminAgentRun } from '$lib/types/admin';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  let statusFilter = $state('all');
  let typeFilter = $state('all');
  let providerFilter = $state('all');
  let ownerFilter = $state('all');
  let fromDate = $state('');
  let toDate = $state('');
  let selectedRunId = $state<string | null>(null);

  const runs = $derived(data.agentRuns.runs);
  const statuses = $derived(uniqueOptions(runs.map((run) => run.status)));
  const runTypes = $derived(uniqueOptions(runs.map((run) => run.runType)));
  const providers = $derived(uniqueOptions(runs.map((run) => run.provider ?? 'unknown')));
  const owners = $derived(uniqueOptions(runs.map((run) => ownerLabel(run))));

  const filteredRuns = $derived(
    runs.filter((run) => {
      const owner = ownerLabel(run);
      const created = run.createdAt ? new Date(run.createdAt) : null;
      const from = fromDate ? new Date(`${fromDate}T00:00:00`) : null;
      const to = toDate ? new Date(`${toDate}T23:59:59`) : null;

      return (
        (statusFilter === 'all' || run.status === statusFilter) &&
        (typeFilter === 'all' || run.runType === typeFilter) &&
        (providerFilter === 'all' || (run.provider ?? 'unknown') === providerFilter) &&
        (ownerFilter === 'all' || owner === ownerFilter) &&
        (!from || (created && created >= from)) &&
        (!to || (created && created <= to))
      );
    })
  );

  const selectedRun = $derived(filteredRuns.find((run) => run.id === selectedRunId) ?? null);

  function uniqueOptions(values: string[]) {
    return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b));
  }

  function label(value: string | null | undefined) {
    return value?.replaceAll('_', ' ').replaceAll(':', ' / ') ?? 'Unknown';
  }

  function ownerLabel(run: AdminAgentRun) {
    return run.userEmail ?? run.workspaceName ?? run.userId ?? run.workspaceId ?? 'unknown owner';
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
    if (['failed', 'failure', 'error'].includes(normalized)) return 'failed';
    if (['running', 'queued', 'pending', 'processing'].includes(normalized)) return 'running';
    if (['completed', 'success', 'ready', 'valid', 'draft'].includes(normalized)) return 'completed';
    return 'neutral';
  }
</script>

<AppShell
  title="Agent Runs"
  subtitle="Read-only operational feed normalized from generation, extraction, analysis, Smart Edit, and assistant tables."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="agents-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a class="active" href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/elements">Elements</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
    </nav>

    <section class="filters" aria-label="Agent run filters">
      <label>
        Status
        <select bind:value={statusFilter}>
          <option value="all">All statuses</option>
          {#each statuses as status}
            <option value={status}>{label(status)}</option>
          {/each}
        </select>
      </label>
      <label>
        Run type
        <select bind:value={typeFilter}>
          <option value="all">All run types</option>
          {#each runTypes as runType}
            <option value={runType}>{label(runType)}</option>
          {/each}
        </select>
      </label>
      <label>
        Provider
        <select bind:value={providerFilter}>
          <option value="all">All providers</option>
          {#each providers as provider}
            <option value={provider}>{provider}</option>
          {/each}
        </select>
      </label>
      <label>
        User / workspace
        <select bind:value={ownerFilter}>
          <option value="all">All owners</option>
          {#each owners as owner}
            <option value={owner}>{owner}</option>
          {/each}
        </select>
      </label>
      <label>
        From
        <input type="date" bind:value={fromDate} />
      </label>
      <label>
        To
        <input type="date" bind:value={toDate} />
      </label>
    </section>

    <section class="agents-layout">
      <article class="panel agents-table-panel">
        <div class="table-head">
          <div>
            <p class="eyebrow">Recent activity</p>
            <h2>{filteredRuns.length} of {data.agentRuns.total} runs</h2>
          </div>
          <a class="button secondary" href="/admin/agents?limit=250">Load 250</a>
        </div>

        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Type</th>
                <th>Deck</th>
                <th>User / workspace</th>
                <th>Provider / model</th>
                <th>Status</th>
                <th>Started</th>
                <th>Updated</th>
                <th>Completed</th>
                <th>Slides</th>
                <th>Artifacts</th>
                <th>Request</th>
              </tr>
            </thead>
            <tbody>
              {#each filteredRuns as run}
                <tr class:active={selectedRunId === run.id}>
                  <td>
                    <button class="run-link" type="button" onclick={() => (selectedRunId = run.id)}>
                      {run.id}
                    </button>
                  </td>
                  <td>{label(run.runType)}</td>
                  <td>{run.deckTitle ?? run.deckId ?? 'No deck'}</td>
                  <td>{ownerLabel(run)}</td>
                  <td>{run.provider ?? 'unknown'} / {run.model ?? 'n/a'}</td>
                  <td><span class={`status ${statusTone(run.status)}`}>{label(run.status)}</span></td>
                  <td>{formatDate(run.createdAt)}</td>
                  <td>{formatDate(run.updatedAt)}</td>
                  <td>{formatDate(run.completedAt)}</td>
                  <td>{run.selectedSlideCount}</td>
                  <td>{run.artifactCount}</td>
                  <td>{run.requestId ?? 'n/a'}</td>
                </tr>
              {:else}
                <tr>
                  <td colspan="12" class="empty">No runs match the current filters.</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </article>

      <aside class="panel detail-panel" aria-live="polite">
        {#if selectedRun}
          <div class="detail-head">
            <div>
              <p class="eyebrow">Run detail</p>
              <h2>{label(selectedRun.runType)}</h2>
            </div>
            <span class={`status ${statusTone(selectedRun.status)}`}>{label(selectedRun.status)}</span>
          </div>
          <a class="button secondary detail-link" href={`/admin/agents/${encodeURIComponent(selectedRun.id)}`}>Open detail page</a>
          <dl>
            <div><dt>Run ID</dt><dd>{selectedRun.id}</dd></div>
            <div><dt>Deck</dt><dd>{selectedRun.deckTitle ?? selectedRun.deckId ?? 'No deck context'}</dd></div>
            <div><dt>Workspace</dt><dd>{selectedRun.workspaceName ?? selectedRun.workspaceId ?? 'n/a'}</dd></div>
            <div><dt>User</dt><dd>{selectedRun.userEmail ?? selectedRun.userId ?? 'n/a'}</dd></div>
            <div><dt>Provider</dt><dd>{selectedRun.provider ?? 'unknown'}</dd></div>
            <div><dt>Model</dt><dd>{selectedRun.model ?? 'n/a'}</dd></div>
            <div><dt>Request ID</dt><dd>{selectedRun.requestId ?? 'n/a'}</dd></div>
            <div><dt>Started</dt><dd>{formatDate(selectedRun.createdAt)}</dd></div>
            <div><dt>Updated</dt><dd>{formatDate(selectedRun.updatedAt)}</dd></div>
            <div><dt>Completed</dt><dd>{formatDate(selectedRun.completedAt)}</dd></div>
          </dl>
          <pre>{JSON.stringify(selectedRun.metadata, null, 2)}</pre>
        {:else}
          <p class="muted">Select a run ID to inspect normalized metadata, ownership, timestamps, and counts.</p>
        {/if}
      </aside>
    </section>
  </section>
</AppShell>

<style>
  .agents-page,
  .agents-layout {
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

  .filters select,
  .filters input {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    color: var(--text);
    padding: 0.55rem 0.65rem;
  }

  .agents-layout {
    grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
    align-items: start;
  }

  .agents-table-panel,
  .detail-panel {
    padding: 1rem;
  }

  .table-head,
  .detail-head {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
    margin-bottom: 1rem;
  }

  .table-head h2,
  .table-head p,
  .detail-head h2,
  .detail-head p {
    margin: 0;
  }

  .table-scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    min-width: 1120px;
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

  tr.active td {
    background: rgba(14, 165, 233, 0.08);
  }

  .run-link {
    max-width: 150px;
    border: 0;
    padding: 0;
    background: transparent;
    color: #bae6fd;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-align: left;
  }

  .status {
    display: inline-flex;
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.22rem 0.5rem;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .status.failed {
    border-color: rgba(248, 113, 113, 0.45);
    color: #fecaca;
  }

  .status.running {
    border-color: rgba(250, 204, 21, 0.45);
    color: #fde68a;
  }

  .status.completed {
    border-color: rgba(52, 211, 153, 0.45);
    color: #bbf7d0;
  }

  .empty {
    color: var(--text-muted);
    text-align: center;
  }

  .detail-panel {
    position: sticky;
    top: 1rem;
  }

  .detail-link {
    width: fit-content;
    margin-bottom: 1rem;
  }

  dl {
    display: grid;
    gap: 0.65rem;
    margin: 0;
  }

  dl div {
    display: grid;
    gap: 0.2rem;
    border-top: 1px solid var(--border);
    padding-top: 0.55rem;
  }

  dt {
    color: var(--text-muted);
    font-size: 0.75rem;
  }

  dd {
    margin: 0;
    overflow-wrap: anywhere;
  }

  pre {
    margin: 1rem 0 0;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.45);
    padding: 0.75rem;
    max-height: 240px;
    overflow: auto;
    color: var(--text-muted);
    font-size: 0.76rem;
  }

  @media (max-width: 1080px) {
    .agents-layout {
      grid-template-columns: 1fr;
    }

    .detail-panel {
      position: static;
    }
  }
</style>
