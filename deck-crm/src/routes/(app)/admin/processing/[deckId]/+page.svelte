<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const processing = $derived(data.processing);
  const countCards = $derived(Object.entries(processing.counts));
  const observability = $derived(processing.observability);
  const workflowStatus = $derived(processing.deck.workflowStatus ?? processing.deck.status);
  const workflowPhase = $derived(observability.currentPhaseKey ?? null);
  const workflowJobId = $derived(observability.worker.workflowJobId ?? observability.worker.runId ?? null);
  const observabilityCards = $derived([
    {
      label: 'Worker',
      value: observability.worker.state,
      detail:
        observability.worker.workflowJobType && observability.worker.workflowJobStatus
          ? `${observability.worker.workflowJobType} · ${observability.worker.workflowJobStatus}`
          : observability.worker.message ?? 'n/a'
    },
    {
      label: 'Current phase',
      value: observability.currentPhase ?? 'n/a',
      detail: observability.currentPhaseKey ?? 'n/a'
    },
    {
      label: 'Queue position',
      value: observability.queuePosition !== null ? `#${observability.queuePosition}` : 'n/a',
      detail: observability.worker.queueState ?? 'n/a'
    },
    { label: 'Last error', value: observability.lastError ?? 'n/a', detail: observability.lastError ?? 'No error recorded' },
    { label: 'Artifact status', value: observability.artifactStatus, detail: 'Lived LLM artifacts' },
    { label: 'Brand status', value: observability.brandStatus, detail: 'Brand profile contract' },
    { label: 'Miniature status', value: observability.miniatureStatus, detail: 'Slide thumbnails / previews' },
    { label: 'LLM status', value: observability.llmStatus, detail: 'Generation jobs and provider work' },
    { label: 'Chat status', value: observability.chatStatus, detail: 'Smart Deck chat readiness' },
    { label: 'Visualizer status', value: observability.visualizerStatus, detail: 'Render schema / preview state' },
    { label: 'Export status', value: observability.exportStatus, detail: 'Compiled deck / export readiness' }
  ]);

  function label(value: string | null | undefined) {
    return value?.replaceAll('_', ' ').replaceAll(':', ' / ') ?? 'Unknown';
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

  function statusTone(status: string) {
    const normalized = status.toLowerCase();
    if (['failed', 'failure', 'error'].includes(normalized)) return 'failed';
    if (['running', 'queued', 'pending', 'processing', 'uploaded', 'parsing'].includes(normalized)) return 'running';
    if (['completed', 'success', 'ready', 'valid', 'draft', 'reviewed', 'applied'].includes(normalized)) return 'completed';
    return 'neutral';
  }

  function formatJson(value: unknown) {
    return JSON.stringify(value, null, 2);
  }

  function field(record: Record<string, unknown>, key: string, fallback = 'n/a') {
    const value = record[key];
    if (value === null || value === undefined || value === '') return fallback;
    return String(value);
  }
</script>

<AppShell
  title="Deck Processing"
  subtitle="Read-only processing console for extraction, analysis, generation, design versions, and artifacts."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="processing-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/failure-tickets">Failure tickets</a>
      <a href="/admin/users">Users</a>
      <a class="active" href={`/admin/processing/${encodeURIComponent(processing.deck.id)}`}>Processing</a>
      <a href={`/admin/slides/${encodeURIComponent(processing.deck.id)}`}>Slides</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
    </nav>

    <section class="hero-panel panel">
      <div>
        <p class="eyebrow">Deck</p>
        <h2>{processing.deck.title}</h2>
        <p class="muted">
          {processing.deck.workspaceName ?? processing.deck.workspaceId ?? 'No workspace'} ·
          {processing.deck.userEmail ?? processing.deck.userId ?? 'No user'}
        </p>
      </div>
      <div class="hero-status">
        <span class={`status ${statusTone(workflowStatus)}`}>{label(workflowStatus)}</span>
        {#if workflowJobId}
          <small>{workflowJobId}{workflowPhase ? ` · ${label(workflowPhase)}` : ''}</small>
        {/if}
      </div>
    </section>

    <section class="count-grid" aria-label="Processing counts">
      {#each countCards as [key, value]}
        <article class="panel count-card">
          <span>{label(key)}</span>
          <strong>{value}</strong>
        </article>
      {/each}
    </section>

    <section class="panel observability-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Observability</p>
          <h2>Operational summary</h2>
        </div>
        <span>{observability.currentPhase ?? 'No current phase'}</span>
      </div>
      <div class="observability-grid">
        {#each observabilityCards as card}
          <article class="observability-card">
            <span>{card.label}</span>
            <strong class={`status ${statusTone(String(card.value))}`}>{card.value}</strong>
            <small>{card.detail}</small>
          </article>
        {/each}
      </div>
    </section>

    <section class="main-grid">
      <article class="panel pipeline-panel">
        <p class="eyebrow">Pipeline</p>
        <h2>Current state</h2>
        <div class="pipeline-list">
          {#each processing.pipeline as step}
            <div class="pipeline-step">
              <span class={`status ${statusTone(step.status)}`}>{label(step.status)}</span>
              <strong>{step.label}</strong>
              <small>{step.key}</small>
            </div>
          {/each}
        </div>
      </article>

      <aside class="panel source-panel">
        <p class="eyebrow">Source</p>
        <h2>Input file</h2>
        {#if processing.sourceFile}
          <dl>
            <div><dt>Filename</dt><dd>{processing.sourceFile.originalFilename ?? processing.sourceFile.filename}</dd></div>
            <div><dt>MIME</dt><dd>{processing.sourceFile.mimeType}</dd></div>
            <div><dt>Storage</dt><dd>{processing.sourceFile.storageProvider} · {processing.sourceFile.hasStoragePath ? 'stored' : 'missing path'}</dd></div>
            <div><dt>Size</dt><dd>{processing.sourceFile.size} bytes</dd></div>
            <div><dt>Pages</dt><dd>{processing.sourceFile.pageCount ?? 'n/a'}</dd></div>
            <div><dt>Uploaded</dt><dd>{formatDate(processing.sourceFile.uploadedAt)}</dd></div>
          </dl>
        {:else}
          <p class="muted">No source file is attached to this deck.</p>
        {/if}
      </aside>
    </section>

    <section class="panel structure-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Structure</p>
          <h2>Persisted source preview</h2>
        </div>
        <span>{processing.structurePreview.slides.length} shown</span>
      </div>
      {#if processing.structurePreview.warningCount > 0}
        <div class="warning-list" aria-label="Extraction warnings">
          <strong>{processing.structurePreview.warningCount} extraction warnings</strong>
          {#each processing.structurePreview.warnings as warning}
            <span>
              Slide {warning.slideIndex}
              {warning.sourcePageNumber ? ` · page ${warning.sourcePageNumber}` : ''} · {warning.message}
            </span>
          {/each}
        </div>
      {/if}
      <div class="structure-list">
        {#each processing.structurePreview.slides as slide}
          <article class="structure-slide">
            <header>
              <div>
                <strong>{slide.slideIndex}. {slide.title}</strong>
                <small>{slide.semanticSlideType ?? slide.role} · page {slide.sourcePageNumber ?? 'n/a'}</small>
              </div>
              <span>{slide.blockCount} blocks · {slide.assetCount} assets</span>
            </header>
            {#if slide.textPreview}
              <p>{slide.textPreview}</p>
            {/if}
            <div class="structure-items">
              <div>
                <small>Blocks</small>
                {#each slide.blocks as block}
                  <span>{field(block, 'blockType')} · {field(block, 'textPreview')}</span>
                {:else}
                  <span>No block preview.</span>
                {/each}
              </div>
              <div>
                <small>Assets</small>
                {#each slide.assets as asset}
                  <span>{field(asset, 'assetType')} · {field(asset, 'storageProvider')} · {field(asset, 'hasStoragePath')}</span>
                {:else}
                  <span>No asset preview.</span>
                {/each}
              </div>
            </div>
          </article>
        {:else}
          <p class="muted">No persisted source slide structure is available yet.</p>
        {/each}
      </div>
    </section>

    <section class="timeline-grid">
      <article class="panel record-panel">
        <p class="eyebrow">Extraction</p>
        <h2>Runs</h2>
        <div class="record-list">
          {#each processing.extractionRuns as run}
            <pre>{formatJson(run)}</pre>
          {:else}
            <p class="muted">No extraction runs recorded.</p>
          {/each}
        </div>
      </article>

      <article class="panel record-panel">
        <p class="eyebrow">Generation</p>
        <h2>Jobs</h2>
        <div class="record-list">
          {#each processing.generationJobs as job}
            <pre>{formatJson(job)}</pre>
          {:else}
            <p class="muted">No generation jobs recorded.</p>
          {/each}
        </div>
      </article>

      <article class="panel record-panel">
        <p class="eyebrow">Design</p>
        <h2>Versions</h2>
        <div class="record-list">
          {#each processing.designVersions as version}
            <pre>{formatJson(version)}</pre>
          {:else}
            <p class="muted">No design versions recorded.</p>
          {/each}
        </div>
      </article>

      <article class="panel record-panel">
        <p class="eyebrow">Artifacts</p>
        <h2>LLM artifacts</h2>
        <div class="record-list">
          {#each processing.artifacts as artifact}
            <pre>{formatJson(artifact)}</pre>
          {:else}
            <p class="muted">No artifacts recorded.</p>
          {/each}
        </div>
      </article>
    </section>

    <section class="panel redaction-panel">
      <div>
        <p class="eyebrow">Redaction</p>
        <h2>Safe admin view</h2>
        <p>{processing.redaction.detailPolicy}</p>
        {#if observability.lastError}
          <p class="error-message"><strong>Latest error:</strong> {observability.lastError}</p>
        {/if}
      </div>
      <div class="redacted-list" aria-label="Redacted fields">
        {#each processing.redaction.sensitiveFieldsRedacted as field}
          <span>{field}</span>
        {/each}
      </div>
    </section>
  </section>
</AppShell>

<style>
  .processing-page,
  .pipeline-list,
  .record-list {
    display: grid;
    gap: 1rem;
  }

  .observability-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  }

  .observability-card {
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.85rem 1rem;
    background: var(--surface);
    display: grid;
    gap: 0.35rem;
  }

  .observability-card span,
  .observability-card small {
    color: var(--text-muted);
  }

  .observability-card strong {
    font-size: 1rem;
    text-wrap: balance;
    overflow-wrap: anywhere;
  }

  .error-message {
    margin-top: 1rem;
    color: var(--danger);
    text-wrap: balance;
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

  .hero-panel,
  .main-grid,
  .timeline-grid,
  .redaction-panel {
    display: grid;
    gap: 1rem;
  }

  .hero-panel {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
    padding: 1rem;
  }

  .hero-panel h2,
  .hero-panel p,
  .pipeline-panel h2,
  .pipeline-panel p,
  .source-panel h2,
  .source-panel p,
  .record-panel h2,
  .record-panel p,
  .redaction-panel h2,
  .redaction-panel p {
    margin: 0;
  }

  .count-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.75rem;
  }

  .count-card,
  .pipeline-panel,
  .source-panel,
  .record-panel,
  .redaction-panel {
    padding: 1rem;
  }

  .section-heading,
  .structure-slide header,
  .structure-items {
    display: grid;
    gap: 0.75rem;
  }

  .section-heading,
  .structure-slide header {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
  }

  .section-heading h2,
  .section-heading p,
  .structure-slide p {
    margin: 0;
  }

  .section-heading span,
  .structure-slide header span,
  .structure-slide small,
  .structure-items small {
    color: var(--text-muted);
  }

  .structure-list {
    display: grid;
    gap: 0.75rem;
    margin-top: 1rem;
  }

  .warning-list {
    display: grid;
    gap: 0.45rem;
    margin-top: 1rem;
    border: 1px solid color-mix(in srgb, #f59e0b 42%, var(--border));
    border-radius: 8px;
    padding: 0.75rem;
    background: color-mix(in srgb, #f59e0b 10%, var(--surface));
  }

  .warning-list span {
    overflow-wrap: anywhere;
    color: var(--text-muted);
    font-size: 0.85rem;
  }

  .structure-slide {
    display: grid;
    gap: 0.75rem;
    border-top: 1px solid var(--border);
    padding-top: 0.85rem;
  }

  .structure-slide header div {
    display: grid;
    gap: 0.2rem;
    min-width: 0;
  }

  .structure-slide strong,
  .structure-slide p,
  .structure-items span {
    overflow-wrap: anywhere;
  }

  .structure-items {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .structure-items div {
    display: grid;
    gap: 0.35rem;
    align-content: start;
  }

  .structure-items span {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.45rem 0.55rem;
    color: var(--text-muted);
    background: var(--surface-subtle);
    font-size: 0.8rem;
  }

  .count-card {
    display: grid;
    gap: 0.35rem;
  }

  .count-card span {
    color: var(--text-muted);
  }

  .count-card strong {
    font-size: 1.5rem;
  }

  .main-grid {
    grid-template-columns: minmax(0, 1fr) minmax(280px, 380px);
    align-items: start;
  }

  .timeline-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .pipeline-step {
    display: grid;
    grid-template-columns: 110px minmax(0, 1fr);
    gap: 0.3rem 0.75rem;
    align-items: center;
    border-top: 1px solid var(--border);
    padding-top: 0.7rem;
  }

  .pipeline-step small {
    grid-column: 2;
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

  dl {
    display: grid;
    gap: 0.65rem;
    margin: 0;
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

  pre {
    margin: 0;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    padding: 0.75rem;
    max-height: 300px;
    overflow: auto;
    color: var(--text-muted);
    font-size: 0.75rem;
    line-height: 1.45;
  }

  .redaction-panel {
    grid-template-columns: minmax(0, 1fr) minmax(280px, 0.8fr);
    align-items: start;
  }

  .redacted-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  @media (max-width: 980px) {
    .hero-panel,
    .main-grid,
    .timeline-grid,
    .redaction-panel,
    .section-heading,
    .structure-slide header,
    .structure-items {
      grid-template-columns: 1fr;
    }
  }
</style>
