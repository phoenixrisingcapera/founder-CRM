<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { AdminTelemetryEvent } from '$lib/types/admin';
  import type { ActionData, PageData } from './$types';

  let { data, form }: { data: PageData; form: ActionData } = $props();

  let selectedEventId = $state<string | null>(null);

  const events = $derived(data.telemetry.events);
  const selectedEvent = $derived(events.find((event) => event.id === selectedEventId) ?? events[0] ?? null);
  const topRunTypes = $derived(topCounts(data.metrics.runTypeCounts, 5));
  const topFailureCategories = $derived(topCounts(data.metrics.failureCategoryCounts, 4));
  const extractionMetrics = $derived(
    data.metrics.extraction ?? {
      summary: {
        totalRuns: 0,
        completedRuns: 0,
        failedRuns: 0,
        activeRuns: 0,
        totalSlides: 0,
        totalBlocks: 0,
        totalAssets: 0,
        partialErrorCount: 0,
        slidesWithPartialErrors: 0
      },
      statusCounts: {},
      runTypeCounts: {},
      extractorCounts: {},
      sourceFormatCounts: {},
      textSourceCounts: {},
      assetTypeCounts: {}
    }
  );
  const topTextSources = $derived(topCounts(extractionMetrics.textSourceCounts, 4));
  const topAssetTypes = $derived(topCounts(extractionMetrics.assetTypeCounts, 4));
  const summaryCards = $derived([
    { label: 'Telemetry events', value: data.metrics.summary.totalEvents, detail: `${data.telemetry.summary.returned} visible` },
    { label: 'Failures', value: data.metrics.summary.failedEvents, detail: `${data.failures.summary.returned} recent` },
    { label: 'Running events', value: data.metrics.summary.runningEvents, detail: 'Currently observed' },
    { label: 'Completions', value: data.metrics.summary.completedEvents, detail: 'Completed event status' },
    { label: 'Extraction runs', value: extractionMetrics.summary.totalRuns, detail: `${extractionMetrics.summary.failedRuns} failed` },
    {
      label: 'Partial pages',
      value: extractionMetrics.summary.slidesWithPartialErrors,
      detail: `${extractionMetrics.summary.partialErrorCount} warnings`
    },
    { label: 'User decisions', value: userDecisionCount(data.telemetry.summary.eventCounts), detail: 'Accept / keep / compile' },
    {
      label: 'Avg latency',
      value: data.metrics.summary.averageLatencyMs === null ? 'n/a' : `${data.metrics.summary.averageLatencyMs}ms`,
      detail: 'Timed telemetry events'
    }
  ]);

  function userDecisionCount(counts: Record<string, number>) {
    return (counts['ai.user.accepted_generated'] ?? 0) + (counts['ai.user.kept_original'] ?? 0) + (counts['ai.final_deck.compiled'] ?? 0);
  }

  function topCounts(counts: Record<string, number>, limit: number) {
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, limit);
  }

  function label(value: string | null | undefined) {
    return value?.replaceAll('_', ' ').replaceAll('.', ' / ') ?? 'Unknown';
  }

  function formatDate(value: string | null | undefined) {
    if (!value) return 'n/a';
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(value));
  }

  function eventTone(event: AdminTelemetryEvent) {
    if (event.eventLevel === 'error' || event.status === 'failed' || event.eventName.endsWith('.failed')) return 'failed';
    if (event.status === 'completed' || event.eventName.endsWith('.completed')) return 'completed';
    if (event.status === 'running') return 'running';
    return 'neutral';
  }

  function filterHref(overrides: Record<string, string | number | null>) {
    const params = new URLSearchParams();
    const merged = { ...data.filters, ...overrides };
    for (const [key, value] of Object.entries(merged)) {
      if (value !== null && value !== '' && value !== undefined) params.set(key, String(value));
    }
    return `/admin/telemetry${params.toString() ? `?${params.toString()}` : ''}`;
  }
</script>

<AppShell
  title="Agent Telemetry"
  subtitle="Redacted production telemetry for AI runs, validation, persistence, review decisions, and final deck compilation."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="telemetry-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a class="active" href="/admin/telemetry">Telemetry</a>
      <a href="/admin/elements">Elements</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
    </nav>

    <section class="summary-grid" aria-label="Telemetry summary">
      {#each summaryCards as card}
        <article class="panel summary-card">
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.detail}</small>
        </article>
      {/each}
    </section>

    <article class="panel filters-panel">
      <form method="GET" class="filters">
        <label>
          Run ID
          <input name="runId" value={data.filters.runId} placeholder="airun_..." />
        </label>
        <label>
          Deck ID
          <input name="deckId" value={data.filters.deckId} placeholder="deck_..." />
        </label>
        <label>
          Run type
          <input name="runType" value={data.filters.runType} placeholder="dididecks_orchestration" />
        </label>
        <label>
          Status
          <select name="status" value={data.filters.status}>
            <option value="">All</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </label>
        <label>
          Event
          <input name="eventName" value={data.filters.eventName} placeholder="ai.run.completed" />
        </label>
        <label>
          Limit
          <select name="limit" value={String(data.filters.limit)}>
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="250">250</option>
          </select>
        </label>
        <button class="button" type="submit">Apply</button>
        <a class="button secondary" href="/admin/telemetry">Reset</a>
      </form>
    </article>

    <section class="ops-grid" aria-label="Telemetry operations">
      <article class="panel ops-panel observability-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Observability</p>
            <h2>{label(data.observability.mode)}</h2>
          </div>
          <span class={`status ${data.observability.otelEnabled ? 'running' : 'neutral'}`}>
            {data.observability.otelEnabled ? 'OTel on' : 'No-op'}
          </span>
        </div>
        <dl class="compact-dl">
          <div><dt>Service</dt><dd>{data.observability.serviceName}</dd></div>
          <div><dt>Exporter</dt><dd>{data.observability.exporterConfigured ? 'Configured' : 'Not configured'}</dd></div>
          <div><dt>Sample rate</dt><dd>{data.observability.sampleRate}</dd></div>
          <div><dt>Error</dt><dd>{data.observability.error ?? 'n/a'}</dd></div>
        </dl>
      </article>

      <article class="panel ops-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Recent failures</p>
            <h2>{data.failures.summary.returned} events</h2>
          </div>
          <a class="button secondary" href={filterHref({ status: 'failed', limit: 250 })}>Open failures</a>
        </div>
        <div class="failure-list">
          {#each data.failures.failures as failure}
            <article class="failure-item">
              <button class="failure-select" type="button" onclick={() => (selectedEventId = failure.id)}>
                <span class={`status ${eventTone(failure)}`}>{label(failure.errorCategory ?? failure.status ?? 'failed')}</span>
                <strong>{failure.eventName}</strong>
                <small>{failure.runId ?? 'No run'} · {formatDate(failure.createdAt)}</small>
              </button>
              <div class="promotion-actions">
                <form method="POST" action="?/promoteLearning">
                  <input type="hidden" name="eventId" value={failure.id} />
                  <input name="note" placeholder="Learning note" maxlength="500" />
                  <button class="button secondary" type="submit">Learning</button>
                </form>
                <form method="POST" action="?/promoteRegression">
                  <input type="hidden" name="eventId" value={failure.id} />
                  <input name="note" placeholder="Regression note" maxlength="500" />
                  <button class="button secondary" type="submit">Regression</button>
                </form>
              </div>
            </article>
          {:else}
            <p class="muted">No failure telemetry is currently recorded.</p>
          {/each}
        </div>
        {#if form?.promotionError}
          <p class="error-text">{form.promotionError}</p>
        {/if}
      </article>

      <article class="panel ops-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Run type mix</p>
            <h2>{topRunTypes.length} categories</h2>
          </div>
        </div>
        <div class="metric-list">
          {#each topRunTypes as [name, count]}
            <a href={filterHref({ runType: name })}>
              <span>{label(name)}</span>
              <strong>{count}</strong>
            </a>
          {:else}
            <p class="muted">No telemetry categories yet.</p>
          {/each}
        </div>
        <h3>Failure categories</h3>
        <div class="metric-list compact">
          {#each topFailureCategories as [name, count]}
            <span><small>{label(name)}</small><strong>{count}</strong></span>
          {:else}
            <p class="muted">No failures grouped yet.</p>
          {/each}
        </div>
      </article>

      <article class="panel ops-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Deck extraction</p>
            <h2>{extractionMetrics.summary.completedRuns} completed</h2>
          </div>
          <span class={`status ${extractionMetrics.summary.failedRuns > 0 ? 'failed' : extractionMetrics.summary.activeRuns > 0 ? 'running' : 'completed'}`}>
            {extractionMetrics.summary.failedRuns > 0 ? `${extractionMetrics.summary.failedRuns} failed` : `${extractionMetrics.summary.activeRuns} active`}
          </span>
        </div>
        <dl class="compact-dl">
          <div><dt>Slides / blocks / assets</dt><dd>{extractionMetrics.summary.totalSlides} / {extractionMetrics.summary.totalBlocks} / {extractionMetrics.summary.totalAssets}</dd></div>
          <div><dt>Partial warnings</dt><dd>{extractionMetrics.summary.partialErrorCount} warnings on {extractionMetrics.summary.slidesWithPartialErrors} slides</dd></div>
        </dl>
        <h3>Text source mix</h3>
        <div class="metric-list compact">
          {#each topTextSources as [name, count]}
            <span><small>{label(name)}</small><strong>{count}</strong></span>
          {:else}
            <p class="muted">No extracted text source metrics yet.</p>
          {/each}
        </div>
        <h3>Asset output</h3>
        <div class="metric-list compact">
          {#each topAssetTypes as [name, count]}
            <span><small>{label(name)}</small><strong>{count}</strong></span>
          {:else}
            <p class="muted">No extracted asset metrics yet.</p>
          {/each}
        </div>
      </article>
    </section>

    <section class="telemetry-layout">
      <article class="panel events-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Event stream</p>
            <h2>{events.length} redacted events</h2>
          </div>
          <a class="button secondary" href={filterHref({ limit: 250 })}>Load 250</a>
        </div>

        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Event</th>
                <th>Status</th>
                <th>Run</th>
                <th>Provider / model</th>
                <th>Latency</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {#each events as event}
                <tr class:active={selectedEventId === event.id} onclick={() => (selectedEventId = event.id)}>
                  <td>
                    <button class="row-button" type="button" onclick={() => (selectedEventId = event.id)}>
                      <strong>{event.eventName}</strong>
                      <small>{label(event.runType)}</small>
                    </button>
                  </td>
                  <td><span class={`status ${eventTone(event)}`}>{label(event.status ?? event.eventLevel)}</span></td>
                  <td>
                    {#if event.runId}
                      <a href={`/admin/telemetry?runId=${encodeURIComponent(event.runId)}`}>{event.runId}</a>
                    {:else}
                      n/a
                    {/if}
                  </td>
                  <td>{event.provider ?? 'unknown'} / {event.model ?? 'n/a'}</td>
                  <td>{event.latencyMs === null ? 'n/a' : `${event.latencyMs}ms`}</td>
                  <td>{formatDate(event.createdAt)}</td>
                </tr>
              {:else}
                <tr>
                  <td colspan="6" class="empty">No telemetry events match these filters.</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </article>

      <aside class="panel detail-panel" aria-live="polite">
        {#if selectedEvent}
          <div class="panel-head">
            <div>
              <p class="eyebrow">Event detail</p>
              <h2>{selectedEvent.eventName}</h2>
            </div>
            <span class={`status ${eventTone(selectedEvent)}`}>{label(selectedEvent.status ?? selectedEvent.eventLevel)}</span>
          </div>

          <dl>
            <div><dt>Event ID</dt><dd>{selectedEvent.id}</dd></div>
            <div><dt>Run</dt><dd>{selectedEvent.runId ?? 'n/a'}</dd></div>
            <div><dt>Step</dt><dd>{selectedEvent.stepId ?? 'n/a'}</dd></div>
            <div><dt>Deck</dt><dd>{selectedEvent.deckId ?? 'n/a'}</dd></div>
            <div><dt>User</dt><dd>{selectedEvent.userId ?? 'n/a'}</dd></div>
            <div><dt>Error category</dt><dd>{selectedEvent.errorCategory ?? 'n/a'}</dd></div>
            <div><dt>Error message</dt><dd>{selectedEvent.errorMessage ?? 'n/a'}</dd></div>
            <div><dt>Trace / span</dt><dd>{selectedEvent.traceId ?? 'n/a'} / {selectedEvent.spanId ?? 'n/a'}</dd></div>
            <div><dt>Request</dt><dd>{selectedEvent.requestId ?? 'n/a'}</dd></div>
          </dl>

          <h3>Redacted metadata</h3>
          <pre>{JSON.stringify(selectedEvent.metadata, null, 2)}</pre>
        {:else}
          <p class="muted">Select a telemetry event to inspect safe run metadata.</p>
        {/if}
      </aside>
    </section>

    <p class="redaction">{data.telemetry.redaction.detailPolicy}</p>
  </section>
</AppShell>

<style>
  .telemetry-page,
  .telemetry-layout {
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
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.85rem;
  }

  .ops-grid {
    display: grid;
    grid-template-columns: minmax(240px, 0.75fr) minmax(0, 1.35fr) minmax(280px, 0.8fr);
    gap: 1rem;
  }

  .summary-card,
  .filters-panel,
  .events-panel,
  .detail-panel,
  .ops-panel {
    padding: 1rem;
  }

  .summary-card {
    display: grid;
    gap: 0.4rem;
  }

  .summary-card span,
  .summary-card small,
  .row-button small,
  .redaction {
    color: var(--text-muted);
  }

  .summary-card strong {
    font-size: 1.8rem;
  }

  .filters {
    align-items: end;
  }

  .filters label {
    display: grid;
    gap: 0.35rem;
    min-width: 160px;
    color: var(--text-muted);
    font-size: 0.84rem;
  }

  .filters input,
  .filters select {
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
    color: var(--text);
    padding: 0.55rem 0.65rem;
  }

  .telemetry-layout {
    grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
    align-items: start;
  }

  .panel-head {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
    margin-bottom: 1rem;
  }

  .panel-head h2,
  .panel-head p {
    margin: 0;
  }

  .table-scroll {
    overflow-x: auto;
  }

  .failure-list,
  .metric-list {
    display: grid;
    gap: 0.6rem;
  }

  .failure-item {
    display: grid;
    gap: 0.6rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    padding: 0.7rem;
  }

  .failure-select,
  .metric-list a,
  .metric-list span {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.4rem 0.75rem;
    align-items: center;
    border: 0;
    background: transparent;
    color: var(--text);
    padding: 0;
    text-align: left;
    text-decoration: none;
  }

  .metric-list a,
  .metric-list span {
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    padding: 0.7rem;
  }

  .failure-select strong,
  .failure-select small {
    grid-column: 1 / -1;
  }

  .failure-select {
    cursor: pointer;
  }

  .promotion-actions,
  .promotion-actions form {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
  }

  .promotion-actions input {
    min-width: 150px;
    flex: 1 1 150px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
    color: var(--text);
    padding: 0.5rem 0.6rem;
  }

  .error-text {
    color: var(--danger);
    margin: 0.8rem 0 0;
  }

  .metric-list.compact {
    margin-top: 0.5rem;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    min-width: 760px;
  }

  th,
  td {
    padding: 0.7rem;
    border-bottom: 1px solid var(--border);
    text-align: left;
    vertical-align: top;
  }

  th {
    color: var(--text-muted);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0;
  }

  tr.active {
    background: var(--surface-subtle);
  }

  .row-button {
    display: grid;
    gap: 0.25rem;
    border: 0;
    background: transparent;
    color: inherit;
    padding: 0;
    text-align: left;
    cursor: pointer;
  }

  .status {
    display: inline-flex;
    border-radius: 999px;
    padding: 0.22rem 0.55rem;
    border: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 0.78rem;
  }

  .status.completed {
    color: var(--success);
    border-color: color-mix(in srgb, var(--success) 42%, transparent);
  }

  .status.failed {
    color: var(--danger);
    border-color: color-mix(in srgb, var(--danger) 42%, transparent);
  }

  .status.running {
    color: var(--accent);
    border-color: color-mix(in srgb, var(--accent) 42%, transparent);
  }

  dl {
    display: grid;
    gap: 0.75rem;
    margin: 0;
  }

  .compact-dl {
    gap: 0.55rem;
  }

  dl div {
    display: grid;
    gap: 0.2rem;
  }

  dt {
    color: var(--text-muted);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0;
  }

  dd {
    margin: 0;
    overflow-wrap: anywhere;
  }

  h3 {
    margin: 1rem 0 0.5rem;
  }

  pre {
    max-height: 360px;
    overflow: auto;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.8rem;
    background: var(--surface-subtle);
    color: var(--text);
    font-size: 0.82rem;
  }

  .empty {
    color: var(--text-muted);
    text-align: center;
  }

  @media (max-width: 980px) {
    .ops-grid,
    .telemetry-layout {
      grid-template-columns: 1fr;
    }
  }
</style>
