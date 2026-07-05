<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { AdminLearningCandidateRun, AdminLearningMemory } from '$lib/types/admin';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  let typeFilter = $state('all');
  let statusFilter = $state('all');
  let selectedMemoryId = $state<string | null>(null);

  const memories = $derived(data.learning.memories);
  const memoryTypes = $derived(uniqueOptions(memories.map((memory) => memory.memoryType)));
  const statuses = $derived(uniqueOptions(memories.map((memory) => memory.status)));
  const filteredMemories = $derived(
    memories.filter(
      (memory) =>
        (typeFilter === 'all' || memory.memoryType === typeFilter) &&
        (statusFilter === 'all' || memory.status === statusFilter)
    )
  );
  const selectedMemory = $derived(filteredMemories.find((memory) => memory.id === selectedMemoryId) ?? null);

  const summaryCards = $derived([
    { label: 'Learning memories', value: data.learning.summary.total, detail: `${data.learning.summary.returned} visible` },
    { label: 'Reflections', value: data.learning.summary.reflectionCount, detail: 'Failure-derived plans' },
    { label: 'Exemplars', value: data.learning.summary.exemplarCount, detail: 'Review-ready examples' },
    { label: 'Insights', value: data.learning.summary.insightCount, detail: 'Distilled rules' },
    { label: 'Candidate runs', value: data.learning.summary.candidateRuns, detail: 'Need learning review' }
  ]);

  function uniqueOptions(values: string[]) {
    return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b));
  }

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

  function ownerLabel(item: AdminLearningMemory | AdminLearningCandidateRun) {
    return item.userEmail ?? item.workspaceName ?? item.userId ?? item.workspaceId ?? 'unknown owner';
  }

  function memoryTone(memory: AdminLearningMemory) {
    if ((memory.feedbackLabel ?? '').toLowerCase() === 'failure' || memory.score < 0) return 'failed';
    if (memory.score > 0) return 'completed';
    return 'neutral';
  }
</script>

<AppShell
  title="Agent Learning"
  subtitle="Reviewable nonparametric learning memory from Smart Deck runs, reflections, exemplars, and distilled insights."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="learning-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a class="active" href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/elements">Elements</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
    </nav>

    <section class="summary-grid" aria-label="Learning memory summary">
      {#each summaryCards as card}
        <article class="panel summary-card">
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.detail}</small>
        </article>
      {/each}
    </section>

    <section class="learning-layout">
      <article class="panel memory-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Stored memory</p>
            <h2>{filteredMemories.length} records</h2>
          </div>
          <a class="button secondary" href="/admin/learning?limit=250">Load 250</a>
        </div>

        <section class="filters" aria-label="Learning memory filters">
          <label>
            Type
            <select bind:value={typeFilter}>
              <option value="all">All types</option>
              {#each memoryTypes as memoryType}
                <option value={memoryType}>{label(memoryType)}</option>
              {/each}
            </select>
          </label>
          <label>
            Status
            <select bind:value={statusFilter}>
              <option value="all">All statuses</option>
              {#each statuses as status}
                <option value={status}>{label(status)}</option>
              {/each}
            </select>
          </label>
        </section>

        <div class="memory-list">
          {#each filteredMemories as memory}
            <button
              class:active={selectedMemoryId === memory.id}
              class="memory-row"
              type="button"
              onclick={() => (selectedMemoryId = memory.id)}
            >
              <span class={`status ${memoryTone(memory)}`}>{label(memory.memoryType)}</span>
              <strong>{memory.title}</strong>
              <small>{memory.deckTitle ?? memory.deckId ?? 'No deck'} · {ownerLabel(memory)}</small>
              <p>{memory.content}</p>
            </button>
          {:else}
            <p class="muted">No learning memories have been recorded yet. Marking an active generation run failed creates the first reviewed reflection.</p>
          {/each}
        </div>
      </article>

      <aside class="panel detail-panel" aria-live="polite">
        {#if selectedMemory}
          <div class="panel-head">
            <div>
              <p class="eyebrow">Memory detail</p>
              <h2>{label(selectedMemory.memoryType)}</h2>
            </div>
            <span class={`status ${memoryTone(selectedMemory)}`}>{selectedMemory.feedbackLabel ?? selectedMemory.status}</span>
          </div>
          <dl>
            <div><dt>Memory ID</dt><dd>{selectedMemory.id}</dd></div>
            <div><dt>Source run</dt><dd>{selectedMemory.sourceRunId ?? 'n/a'}</dd></div>
            <div><dt>Deck</dt><dd>{selectedMemory.deckTitle ?? selectedMemory.deckId ?? 'n/a'}</dd></div>
            <div><dt>User / workspace</dt><dd>{ownerLabel(selectedMemory)}</dd></div>
            <div><dt>Score</dt><dd>{selectedMemory.score}</dd></div>
            <div><dt>Created</dt><dd>{formatDate(selectedMemory.createdAt)}</dd></div>
            <div><dt>Updated</dt><dd>{formatDate(selectedMemory.updatedAt)}</dd></div>
          </dl>
          <pre>{JSON.stringify(selectedMemory.evidence, null, 2)}</pre>
        {:else}
          <p class="muted">Select a learning memory to inspect its source, score, tags, and redacted evidence.</p>
        {/if}
      </aside>
    </section>

    <article class="panel candidate-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Review queue</p>
          <h2>Failed runs without memory</h2>
        </div>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Run</th>
              <th>Deck</th>
              <th>User / workspace</th>
              <th>Provider / model</th>
              <th>Status</th>
              <th>Slides</th>
              <th>Updated</th>
              <th>Failure signal</th>
            </tr>
          </thead>
          <tbody>
            {#each data.learning.candidateRuns as run}
              <tr>
                <td><a href={`/admin/agents/${encodeURIComponent(run.id)}`}>{run.id}</a></td>
                <td>{run.deckTitle ?? run.deckId ?? 'No deck'}</td>
                <td>{ownerLabel(run)}</td>
                <td>{run.provider ?? 'unknown'} / {run.model ?? 'n/a'}</td>
                <td><span class="status failed">{label(run.status)}</span></td>
                <td>{run.selectedSlideCount}</td>
                <td>{formatDate(run.updatedAt)}</td>
                <td>{run.errorPreview ?? 'No error preview'}</td>
              </tr>
            {:else}
              <tr>
                <td colspan="8" class="empty">No failed generation runs are waiting for learning review.</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="redaction">{data.learning.redaction.detailPolicy}</p>
    </article>
  </section>
</AppShell>

<style>
  .learning-page,
  .learning-layout {
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

  .summary-card,
  .memory-panel,
  .detail-panel,
  .candidate-panel {
    padding: 1rem;
  }

  .summary-card {
    display: grid;
    gap: 0.4rem;
  }

  .summary-card span,
  .summary-card small,
  .memory-row small,
  .memory-row p,
  .redaction {
    color: var(--text-muted);
  }

  .summary-card strong {
    font-size: 1.8rem;
  }

  .learning-layout {
    grid-template-columns: minmax(0, 1fr) minmax(280px, 380px);
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

  .filters {
    align-items: end;
    margin-bottom: 1rem;
  }

  .filters label {
    display: grid;
    gap: 0.35rem;
    min-width: 160px;
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

  .memory-list {
    display: grid;
    gap: 0.6rem;
  }

  .memory-row {
    display: grid;
    grid-template-columns: 120px minmax(0, 1fr);
    gap: 0.35rem 0.75rem;
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    color: inherit;
    padding: 0.75rem;
    text-align: left;
    cursor: pointer;
  }

  .memory-row.active {
    border-color: var(--accent);
  }

  .memory-row small,
  .memory-row p {
    grid-column: 2;
    margin: 0;
  }

  .status {
    display: inline-flex;
    width: fit-content;
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

  .status.completed {
    border-color: rgba(52, 211, 153, 0.45);
    color: #bbf7d0;
  }

  .detail-panel {
    position: sticky;
    top: 1rem;
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

  td a {
    color: #bae6fd;
  }

  .empty {
    color: var(--text-muted);
    text-align: center;
  }

  .redaction {
    margin: 0.8rem 0 0;
    font-size: 0.8rem;
  }

  @media (max-width: 1080px) {
    .learning-layout {
      grid-template-columns: 1fr;
    }

    .detail-panel {
      position: static;
    }
  }
</style>
