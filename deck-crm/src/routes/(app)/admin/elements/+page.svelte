<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const payload = $derived(data.elements);
  let typeFilter = $state('all');
  let statusFilter = $state('all');
  let visibilityFilter = $state('all');
  let selectedElementId = $state<string | null>(null);

  const types = $derived(uniqueOptions(payload.elements.map((element) => element.elementType)));
  const versionStatuses = $derived(
    uniqueOptions(
      payload.elements.flatMap((element) =>
        element.versions.map((version) => String(version.status ?? 'unknown'))
      )
    )
  );

  const filteredElements = $derived(
    payload.elements.filter((element) => {
      const statuses = element.versions.map((version) => String(version.status ?? 'unknown'));
      return (
        (typeFilter === 'all' || element.elementType === typeFilter) &&
        (statusFilter === 'all' || statuses.includes(statusFilter)) &&
        (visibilityFilter === 'all' ||
          (visibilityFilter === 'visible' && element.visible) ||
          (visibilityFilter === 'hidden' && !element.visible))
      );
    })
  );

  const selectedElement = $derived(
    filteredElements.find((element) => element.id === selectedElementId) ?? filteredElements[0] ?? null
  );

  function uniqueOptions(values: string[]) {
    return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b));
  }

  function label(value: string | null | undefined) {
    return value?.replaceAll('_', ' ').replaceAll(':', ' / ') ?? 'Unknown';
  }

  function ownerLabel(element: PageData['elements']['elements'][number]) {
    return element.userEmail ?? element.workspaceName ?? element.userId ?? element.workspaceId ?? 'unknown owner';
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
    if (['failed', 'failure', 'error', 'invalid'].includes(normalized)) return 'failed';
    if (['running', 'queued', 'pending', 'processing'].includes(normalized)) return 'running';
    if (['completed', 'success', 'ready', 'valid', 'active', 'draft'].includes(normalized)) return 'completed';
    return 'neutral';
  }

  function formatJson(value: unknown) {
    return JSON.stringify(value, null, 2);
  }
</script>

<AppShell
  title="Element Inspector"
  subtitle="Read-only generated element feed with versions, variation jobs, geometry, and ownership context."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="elements-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a class="active" href="/admin/elements">Elements</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
      {#if payload.filters.deckId}
        <a href={`/admin/slides/${encodeURIComponent(payload.filters.deckId)}`}>Deck slides</a>
        <a href={`/admin/processing/${encodeURIComponent(payload.filters.deckId)}`}>Deck processing</a>
      {/if}
    </nav>

    <section class="summary-grid" aria-label="Element summary">
      <article class="panel summary-card">
        <span>Elements</span>
        <strong>{filteredElements.length}</strong>
        <small>{payload.total} total returned</small>
      </article>
      {#each Object.entries(payload.typeCounts) as [type, count]}
        <article class="panel summary-card">
          <span>{label(type)}</span>
          <strong>{count}</strong>
          <small>element type</small>
        </article>
      {/each}
    </section>

    <section class="filters" aria-label="Element filters">
      <label>
        Type
        <select bind:value={typeFilter}>
          <option value="all">All types</option>
          {#each types as type}
            <option value={type}>{label(type)}</option>
          {/each}
        </select>
      </label>
      <label>
        Version status
        <select bind:value={statusFilter}>
          <option value="all">All statuses</option>
          {#each versionStatuses as status}
            <option value={status}>{label(status)}</option>
          {/each}
        </select>
      </label>
      <label>
        Visibility
        <select bind:value={visibilityFilter}>
          <option value="all">All elements</option>
          <option value="visible">Visible</option>
          <option value="hidden">Hidden</option>
        </select>
      </label>
      <a class="button secondary" href="/admin/elements?limit=250">Load 250</a>
    </section>

    <section class="elements-layout">
      <article class="panel table-panel">
        <div class="table-head">
          <div>
            <p class="eyebrow">Generated elements</p>
            <h2>{filteredElements.length} visible rows</h2>
          </div>
        </div>

        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Element</th>
                <th>Type</th>
                <th>Deck</th>
                <th>Slide</th>
                <th>Version</th>
                <th>Geometry</th>
                <th>Flags</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {#each filteredElements as element}
                <tr class:active={selectedElement?.id === element.id}>
                  <td>
                    <button class="element-link" type="button" onclick={() => (selectedElementId = element.id)}>
                      {element.elementKey}
                    </button>
                    <small>{element.id}</small>
                  </td>
                  <td>{label(element.elementType)}</td>
                  <td>{element.deckTitle ?? element.deckId}<br /><small>{ownerLabel(element)}</small></td>
                  <td>
                    {element.generatedSlideTitle ?? element.generatedSlideId}
                    <br /><small>{element.sourceSlideTitle ?? element.sourceSlideId ?? 'No source slide'}</small>
                  </td>
                  <td>
                    <span class={`status ${statusTone(String(element.versions[0]?.status ?? 'unknown'))}`}>
                      {label(String(element.versions[0]?.status ?? 'unknown'))}
                    </span>
                    <br /><small>{element.versionCount} versions · {element.variationJobCount} jobs</small>
                  </td>
                  <td>{element.geometry.width}x{element.geometry.height} @ {element.geometry.x},{element.geometry.y}</td>
                  <td>{element.visible ? 'visible' : 'hidden'} · {element.locked ? 'locked' : 'editable'}</td>
                  <td>{formatDate(element.updatedAt)}</td>
                </tr>
              {:else}
                <tr>
                  <td colspan="8" class="empty">No generated elements match the current filters.</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </article>

      <aside class="panel detail-panel" aria-live="polite">
        {#if selectedElement}
          <div class="detail-head">
            <div>
              <p class="eyebrow">Element detail</p>
              <h2>{selectedElement.elementKey}</h2>
            </div>
            <span class={`status ${selectedElement.visible ? 'completed' : 'neutral'}`}>
              {selectedElement.visible ? 'Visible' : 'Hidden'}
            </span>
          </div>

          <dl>
            <div><dt>Element ID</dt><dd>{selectedElement.id}</dd></div>
            <div><dt>Deck</dt><dd>{selectedElement.deckTitle ?? selectedElement.deckId}</dd></div>
            <div><dt>Generated slide</dt><dd>{selectedElement.generatedSlideTitle ?? selectedElement.generatedSlideId}</dd></div>
            <div><dt>Source slide</dt><dd>{selectedElement.sourceSlideTitle ?? selectedElement.sourceSlideId ?? 'n/a'}</dd></div>
            <div><dt>Design version</dt><dd>{selectedElement.designVersionName ?? selectedElement.designVersionId}</dd></div>
            <div><dt>Geometry</dt><dd>{formatJson(selectedElement.geometry)}</dd></div>
            <div><dt>Payload keys</dt><dd>{[...selectedElement.contentKeys, ...selectedElement.styleKeys].join(', ') || 'n/a'}</dd></div>
          </dl>

          <h3>Versions</h3>
          <pre>{formatJson(selectedElement.versions)}</pre>

          <h3>Variation jobs</h3>
          <pre>{formatJson(selectedElement.variationJobs)}</pre>
        {:else}
          <p class="muted">Select an element to inspect versions, variation jobs, and geometry.</p>
        {/if}
      </aside>
    </section>

    <section class="panel redaction-panel">
      <div>
        <p class="eyebrow">Redaction</p>
        <h2>Safe admin view</h2>
        <p>{payload.redaction.detailPolicy}</p>
      </div>
      <div class="redacted-list" aria-label="Redacted fields">
        {#each payload.redaction.sensitiveFieldsRedacted as field}
          <span>{field}</span>
        {/each}
      </div>
    </section>
  </section>
</AppShell>

<style>
  .elements-page,
  .elements-layout {
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
  .detail-panel,
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

  .elements-layout {
    grid-template-columns: minmax(0, 1fr) minmax(300px, 390px);
    align-items: start;
  }

  .table-head,
  .detail-head,
  .redaction-panel {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
  }

  .table-head h2,
  .table-head p,
  .detail-head h2,
  .detail-head p,
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

  tr.active td {
    background: color-mix(in srgb, var(--accent) 8%, transparent);
  }

  td small {
    color: var(--text-muted);
  }

  .element-link {
    max-width: 150px;
    border: 0;
    padding: 0;
    background: transparent;
    color: var(--accent);
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-align: left;
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

  .empty {
    color: var(--text-muted);
    text-align: center;
  }

  .detail-panel {
    position: sticky;
    top: 1rem;
  }

  dl {
    display: grid;
    gap: 0.65rem;
    margin: 0 0 1rem;
  }

  dl div {
    border-top: 1px solid var(--border);
    padding-top: 0.55rem;
  }

  dt {
    color: var(--text-muted);
    font-size: 0.75rem;
  }

  dd {
    margin: 0.2rem 0 0;
    overflow-wrap: anywhere;
  }

  .detail-panel h3 {
    margin: 1rem 0 0.5rem;
    font-size: 0.95rem;
  }

  pre {
    margin: 0;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    padding: 0.75rem;
    max-height: 260px;
    overflow: auto;
    color: var(--text-muted);
    font-size: 0.75rem;
    line-height: 1.45;
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

  @media (max-width: 1080px) {
    .elements-layout,
    .redaction-panel {
      grid-template-columns: 1fr;
    }

    .detail-panel {
      position: static;
    }
  }
</style>
