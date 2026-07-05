<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { AdminAgentRun } from '$lib/types/admin';
  import type { ActionData, PageData } from './$types';

  let { data, form }: { data: PageData; form?: ActionData } = $props();

  const run = $derived(data.detail.run);
  const relatedEntries = $derived(Object.entries(data.detail.related ?? {}));
  const notes = $derived(data.detail.notes ?? []);
  const canControlActiveRun = $derived(['queued', 'running', 'pending', 'processing'].includes(run.status.toLowerCase()));
  const canDiscardDesignVersion = $derived(
    run.runType === 'design_version' && run.status.toLowerCase() === 'draft' && run.metadata?.isActive !== true
  );
  const canRetryGenerationJob = $derived(
    run.runType === 'generation_job' && ['failed', 'canceled'].includes(run.status.toLowerCase())
  );

  function label(value: string | null | undefined) {
    return value?.replaceAll('_', ' ').replaceAll(':', ' / ') ?? 'Unknown';
  }

  function ownerLabel(item: AdminAgentRun) {
    return item.userEmail ?? item.workspaceName ?? item.userId ?? item.workspaceId ?? 'unknown owner';
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

  function formatJson(value: unknown) {
    return JSON.stringify(value, null, 2);
  }
</script>

<AppShell
  title="Agent Run Detail"
  subtitle="Read-only operational metadata and safe related summaries for one normalized agent run."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="run-detail-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/failure-tickets">Failure tickets</a>
      <a href="/admin/users">Users</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a class="active" href={`/admin/agents/${encodeURIComponent(run.id)}`}>Run detail</a>
    </nav>

    <section class="detail-layout">
      <article class="panel run-summary">
        <div class="summary-head">
          <div>
            <p class="eyebrow">Run</p>
            <h2>{label(run.runType)}</h2>
            <p class="muted">{run.id}</p>
          </div>
          <span class={`status ${statusTone(run.status)}`}>{label(run.status)}</span>
        </div>

        <dl class="summary-grid">
          <div><dt>Deck</dt><dd>{run.deckTitle ?? run.deckId ?? 'No deck context'}</dd></div>
          <div><dt>User / workspace</dt><dd>{ownerLabel(run)}</dd></div>
          <div><dt>Provider</dt><dd>{run.provider ?? 'unknown'}</dd></div>
          <div><dt>Model</dt><dd>{run.model ?? 'n/a'}</dd></div>
          <div><dt>Started</dt><dd>{formatDate(run.createdAt)}</dd></div>
          <div><dt>Updated</dt><dd>{formatDate(run.updatedAt)}</dd></div>
          <div><dt>Completed</dt><dd>{formatDate(run.completedAt)}</dd></div>
          <div><dt>Selected slides</dt><dd>{run.selectedSlideCount}</dd></div>
          <div><dt>Artifacts</dt><dd>{run.artifactCount}</dd></div>
          <div><dt>Request ID</dt><dd>{run.requestId ?? 'n/a'}</dd></div>
        </dl>
      </article>

      <div class="side-stack">
        <aside class="panel notes-panel">
          <p class="eyebrow">Admin notes</p>
          <h2>Operational log</h2>
          <form class="note-form" method="POST" action="?/addNote">
            <textarea
              name="note"
              maxlength="2000"
              rows="4"
              aria-label="Add admin note"
              placeholder="Add a short operator note"
            ></textarea>
            {#if form?.noteError}
              <p class="form-error" role="alert">{form.noteError}</p>
            {/if}
            <button type="submit">Add note</button>
          </form>

          <div class="notes-list">
            {#each notes as note}
              <article class="note-entry">
                <p>{note.note ?? 'No note text stored.'}</p>
                <small>{note.actorEmail ?? note.actorUserId ?? 'unknown actor'} · {formatDate(note.createdAt)}</small>
              </article>
            {:else}
              <p class="muted">No admin notes have been added to this run.</p>
            {/each}
          </div>
        </aside>

        <aside class="panel action-panel">
          <p class="eyebrow">Controlled action</p>
          <h2>Run controls</h2>
          {#if canControlActiveRun || canDiscardDesignVersion || canRetryGenerationJob}
            <div class="action-stack">
              {#if canRetryGenerationJob}
                <form class="note-form action-form" method="POST" action="?/retryRun">
                  <p class="muted">Retry creates a new generation run and leaves this original run unchanged.</p>
                  <textarea
                    name="reason"
                    maxlength="500"
                    rows="3"
                    aria-label="Reason for retrying run"
                    placeholder="Reason for audit log"
                  ></textarea>
                  <label class="confirm-row">
                    <input type="checkbox" name="confirm" value="yes" />
                    <span>Confirm a replacement generation run should be created.</span>
                  </label>
                  {#if form?.retryError}
                    <p class="form-error" role="alert">{form.retryError}</p>
                  {/if}
                  <button type="submit">Retry run</button>
                </form>
              {/if}

              {#if canControlActiveRun}
                <form class="note-form action-form" method="POST" action="?/cancelRun">
                  <p class="muted">Cancel stops tracking this active run without recording it as a failure.</p>
                  <textarea
                    name="reason"
                    maxlength="500"
                    rows="3"
                    aria-label="Reason for canceling run"
                    placeholder="Reason for audit log"
                  ></textarea>
                  <label class="confirm-row">
                    <input type="checkbox" name="confirm" value="yes" />
                    <span>Confirm this run should be canceled.</span>
                  </label>
                  {#if form?.cancelError}
                    <p class="form-error" role="alert">{form.cancelError}</p>
                  {/if}
                  <button class="secondary-button" type="submit">Cancel run</button>
                </form>

                <form class="note-form action-form" method="POST" action="?/markFailed">
                  <p class="muted">Mark failed when the run is stuck or known to have failed.</p>
                  <textarea
                    name="reason"
                    maxlength="500"
                    rows="3"
                    aria-label="Reason for marking run failed"
                    placeholder="Reason for audit log"
                  ></textarea>
                  <label class="confirm-row">
                    <input type="checkbox" name="confirm" value="yes" />
                    <span>Confirm this run should be marked failed.</span>
                  </label>
                  {#if form?.markFailedError}
                    <p class="form-error" role="alert">{form.markFailedError}</p>
                  {/if}
                  <button class="danger-button" type="submit">Mark failed</button>
                </form>
              {/if}

              {#if canDiscardDesignVersion}
                <form class="note-form action-form" method="POST" action="?/discardRun">
                  <p class="muted">Discard hides this draft design version from review without deleting generated records.</p>
                  <textarea
                    name="reason"
                    maxlength="500"
                    rows="3"
                    aria-label="Reason for discarding design version"
                    placeholder="Reason for audit log"
                  ></textarea>
                  <label class="confirm-row">
                    <input type="checkbox" name="confirm" value="yes" />
                    <span>Confirm this draft design version should be discarded.</span>
                  </label>
                  {#if form?.discardError}
                    <p class="form-error" role="alert">{form.discardError}</p>
                  {/if}
                  <button class="danger-button" type="submit">Discard draft</button>
                </form>
              {/if}
            </div>
          {:else}
            <p class="muted">This run has no controlled mutation available.</p>
          {/if}
        </aside>

        <aside class="panel redaction-panel">
          <p class="eyebrow">Redaction</p>
          <h2>Safe detail policy</h2>
          <p>{data.detail.redaction.detailPolicy}</p>
          <div class="redacted-list" aria-label="Redacted fields">
            {#each data.detail.redaction.sensitiveFieldsRedacted as field}
              <span>{field}</span>
            {/each}
          </div>
        </aside>
      </div>
    </section>

    <section class="detail-columns">
      <article class="panel detail-panel">
        <p class="eyebrow">Related records</p>
        <h2>Safe operational context</h2>
        <div class="related-list">
          {#each relatedEntries as [key, value]}
            <section class="related-block">
              <h3>{label(key)}</h3>
              <pre>{formatJson(value)}</pre>
            </section>
          {:else}
            <p class="muted">No related records are available for this run.</p>
          {/each}
        </div>
      </article>

      <article class="panel detail-panel">
        <p class="eyebrow">Metadata</p>
        <h2>Normalized run fields</h2>
        <pre>{formatJson(run.metadata)}</pre>
      </article>
    </section>
  </section>
</AppShell>

<style>
  .run-detail-page,
  .detail-panel,
  .related-list,
  .side-stack,
  .notes-list,
  .note-form {
    display: grid;
    gap: 1rem;
  }

  .action-stack {
    display: grid;
    gap: 1.1rem;
  }

  .action-form {
    border-top: 1px solid var(--border);
    padding-top: 0.85rem;
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

  .detail-layout,
  .detail-columns {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(280px, 380px);
    gap: 1rem;
    align-items: start;
  }

  .run-summary,
  .redaction-panel,
  .notes-panel,
  .action-panel,
  .detail-panel {
    padding: 1rem;
  }

  .summary-head {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
    margin-bottom: 1rem;
  }

  .summary-head h2,
  .summary-head p,
  .redaction-panel h2,
  .redaction-panel p,
  .notes-panel h2,
  .notes-panel p,
  .action-panel h2,
  .action-panel p,
  .detail-panel h2,
  .detail-panel p,
  .related-block h3 {
    margin: 0;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.8rem;
    margin: 0;
  }

  .summary-grid div {
    border-top: 1px solid var(--border);
    padding-top: 0.6rem;
  }

  dt {
    color: var(--text-muted);
    font-size: 0.75rem;
  }

  dd {
    margin: 0.2rem 0 0;
    overflow-wrap: anywhere;
  }

  textarea {
    width: 100%;
    resize: vertical;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    color: var(--text);
    padding: 0.75rem;
    font: inherit;
    line-height: 1.45;
  }

  textarea:focus-visible,
  button:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  button {
    justify-self: start;
    border: 1px solid var(--accent);
    border-radius: 8px;
    background: var(--accent);
    color: var(--surface);
    padding: 0.55rem 0.8rem;
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }

  button:hover {
    filter: brightness(0.96);
  }

  button:active {
    transform: translateY(1px);
  }

  .danger-button {
    border-color: var(--danger);
    background: var(--danger);
  }

  .secondary-button {
    border-color: var(--border);
    background: var(--surface-subtle);
    color: var(--text);
  }

  .confirm-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.5rem;
    align-items: start;
    color: var(--text-muted);
    font-size: 0.86rem;
    line-height: 1.35;
  }

  .confirm-row input {
    margin-top: 0.12rem;
    accent-color: var(--danger);
  }

  .form-error {
    color: var(--danger);
    font-size: 0.85rem;
  }

  .note-entry {
    border-top: 1px solid var(--border);
    padding-top: 0.75rem;
    display: grid;
    gap: 0.35rem;
  }

  .note-entry p {
    overflow-wrap: anywhere;
    line-height: 1.45;
  }

  .note-entry small {
    color: var(--text-muted);
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

  .redacted-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.85rem;
  }

  .related-block {
    display: grid;
    gap: 0.5rem;
  }

  .related-block h3 {
    font-size: 0.95rem;
  }

  pre {
    margin: 0;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    padding: 0.75rem;
    max-height: 420px;
    overflow: auto;
    color: var(--text-muted);
    font-size: 0.76rem;
    line-height: 1.45;
  }

  @media (max-width: 980px) {
    .detail-layout,
    .detail-columns {
      grid-template-columns: 1fr;
    }
  }
</style>
