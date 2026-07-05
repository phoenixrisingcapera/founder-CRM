<script lang="ts">
  import ExportOptionCard from '$components/ExportOptionCard.svelte';
  import { deckProductApiPath } from '$lib/contracts';
  import { trackDeckEvent } from '$lib/analytics/deckAnalytics';
  import { waitForWorkflowJobCompletion } from '$lib/api/deckService/workflow.client';
  import type { DeckExport } from '$types/domain';

  interface Props {
    deckId: string;
    exports: DeckExport[];
  }

  let { deckId, exports }: Props = $props();
  let exportRecords = $state<DeckExport[]>([]);
  let selectedExportType = $state<DeckExport['type']>('final_deck');
  let exportStatus = $state<'idle' | 'generating' | 'ready' | 'failed'>('idle');
  let exportError = $state<string | null>(null);
  let includeFindings = $state(true);
  let includeSuggestions = $state(true);
  let includeSmartEdits = $state(true);
  let includeRejected = $state(false);
  let viewedTracked = $state(false);

  type WorkflowExportRequest = {
    type?: string;
    exportType?: string;
    idempotencyKey: string;
  };

  type WorkflowCommandAcceptedResponse = {
    accepted: boolean;
    jobId: string;
    jobType: string;
    status: string;
    phase: string;
    workflowStateUrl: string;
    jobUrl: string;
  };

  $effect(() => {
    exportRecords = exports;
  });

  $effect(() => {
    if (!viewedTracked && deckId) {
      viewedTracked = true;
      void trackDeckEvent(deckId, {
        eventName: 'export.page.viewed',
        surface: 'export_page',
        entityType: 'deck',
        entityId: deckId,
        metadata: { existingExportCount: exportRecords.length }
      });
    }
  });

  const exportOptions = [
    {
      type: 'final_deck',
      title: 'Final deck artifact',
      detail: 'Compiled deck manifest with accepted generated versions and unchanged originals.'
    },
    {
      type: 'diligence_report',
      title: 'Diligence report',
      detail: 'Findings, risks, and audience-fit commentary for investment review.'
    },
    {
      type: 'adapted_outline',
      title: 'Adapted deck outline',
      detail: 'Narrative structure and rewritten framing for the target audience.'
    },
    {
      type: 'change_log',
      title: 'Change log',
      detail: 'Accepted, rejected, and edited AI interventions with audit trace.'
    },
    {
      type: 'annotated_deck_report',
      title: 'Annotated deck report',
      detail: 'Slide-by-slide commentary across diligence, messaging, and Smart Edit.'
    }
  ];

  async function getDeckExports(deckId: string): Promise<DeckExport[]> {
    const response = await fetch(`/api/decks/${deckId}/exports`);
    if (!response.ok) {
      throw new Error(await response.text());
    }

    const payload = await response.json().catch(() => null);
    if (!payload || typeof payload !== 'object') {
      return [];
    }

    const exports = (payload as { exports?: DeckExport[] }).exports;
    return Array.isArray(exports) ? exports : [];
  }

  async function startExportWorkflow(deckId: string, payload: WorkflowExportRequest): Promise<WorkflowCommandAcceptedResponse> {
    const requestType = (payload.type ?? payload.exportType ?? '').trim();
    if (!requestType) {
      throw new Error('Export type is required.');
    }

    const response = await fetch(deckProductApiPath(`/decks/${deckId}/workflows/export`), {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        type: requestType,
        exportType: payload.exportType ?? requestType,
        idempotencyKey: payload.idempotencyKey
      })
    });

    const payloadJson = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(
        typeof payloadJson?.message === 'string'
          ? payloadJson.message
          : 'Could not start export workflow.'
      );
    }

    return payloadJson as WorkflowCommandAcceptedResponse;
  }

  function selectExportType(type: DeckExport['type']) {
    selectedExportType = type;
    void trackDeckEvent(deckId, {
      eventName: 'export.option.selected',
      surface: 'export_page',
      entityType: 'export_option',
      entityId: type,
      metadata: { exportType: type }
    });
  }

  function toggleInclusion(name: 'includeFindings' | 'includeSuggestions' | 'includeSmartEdits' | 'includeRejected', value: boolean) {
    if (name === 'includeFindings') includeFindings = value;
    if (name === 'includeSuggestions') includeSuggestions = value;
    if (name === 'includeSmartEdits') includeSmartEdits = value;
    if (name === 'includeRejected') includeRejected = value;
    void trackDeckEvent(deckId, {
      eventName: 'export.include_toggle.changed',
      surface: 'export_page',
      entityType: 'export_toggle',
      entityId: name,
      metadata: { name, value, exportType: selectedExportType }
    });
  }

  async function generateExport() {
    exportStatus = 'generating';
    exportError = null;
    const clientEventId = `export_${crypto.randomUUID?.() ?? Date.now().toString(36)}`;
    await trackDeckEvent(deckId, {
      eventName: 'export.generate.clicked',
      surface: 'export_page',
      entityType: 'export_option',
      entityId: selectedExportType,
      metadata: {
        clientEventId,
        exportType: selectedExportType,
        includeFindings,
        includeSuggestions,
        includeSmartEdits,
        includeRejected
      }
    });
    try {
      const accepted = await startExportWorkflow(deckId, {
        type: selectedExportType,
        exportType: selectedExportType,
        idempotencyKey: clientEventId
      });
      const existingExportIds = new Set(exportRecords.map((item) => item.id));
      if (!accepted.jobId) {
        throw new Error('Export workflow did not return a job id.');
      }

      const job = await waitForWorkflowJobCompletion(accepted.jobId, 'Export generation failed.');
      if (job.status !== 'completed') {
        throw new Error('Export generation failed to complete.');
      }

      const latestExports = await getDeckExports(deckId);
      const firstArtifactId = Array.isArray(job.artifacts) ? String(job.artifacts[0]?.artifactId || '') : '';
      const candidateById = latestExports.find(
        (item) => item.id === firstArtifactId && firstArtifactId.length > 0
      );
      const candidateByType = latestExports
        .filter((item) => item.type === selectedExportType && !existingExportIds.has(item.id))
        .sort((a, b) => (Date.parse(b.createdAt) || 0) - (Date.parse(a.createdAt) || 0))[0];

      const nextExport = candidateById || candidateByType;
      if (!nextExport) {
        throw new Error('Export generation completed, but output could not be retrieved.');
      }

      exportRecords = [nextExport, ...latestExports.filter((item) => item.id !== nextExport.id)];
      exportStatus = 'ready';
      await trackDeckEvent(deckId, {
        eventName: 'export.generate.succeeded',
        surface: 'export_page',
        entityType: 'deck_export',
        entityId: nextExport.id,
        metadata: { clientEventId, exportType: selectedExportType }
      });
    } catch (error) {
      exportStatus = 'failed';
      exportError = error instanceof Error ? error.message : 'Export generation failed.';
      await trackDeckEvent(deckId, {
        eventName: 'export.generate.failed',
        surface: 'export_page',
        entityType: 'export_option',
        entityId: selectedExportType,
        metadata: { clientEventId, exportType: selectedExportType, message: exportError }
      });
    }
  }

  function trackDownload(item: DeckExport) {
    void trackDeckEvent(deckId, {
      eventName: 'export.download.clicked',
      surface: 'export_page',
      entityType: 'deck_export',
      entityId: item.id,
      metadata: { exportType: item.type }
    });
  }
</script>

<section class="panel export-panel">
  <div class="export-grid">
    <div class="section-stack">
      <section class="header">
        <div>
          <div class="eyebrow">Export select output</div>
          <h3>Generate a review-ready artifact</h3>
          <p class="muted">Choose the output type and control which findings, audience recommendations, and Smart Edit changes are included.</p>
        </div>
      </section>

      <div class="options">
        {#each exportOptions as option}
          <button
            class="option-button"
            type="button"
            class:selected={selectedExportType === option.type}
            onclick={() => selectExportType(option.type)}
          >
            <ExportOptionCard
              title={option.title}
              detail={option.detail}
              state={selectedExportType === option.type ? 'selected' : exportRecords.some((item) => item.type === option.type) ? 'ready' : 'idle'}
            />
          </button>
        {/each}
      </div>

      <section class="inclusion-panel">
        <div class="eyebrow">Include</div>
        <label><input type="checkbox" checked={includeFindings} onchange={(event) => toggleInclusion('includeFindings', event.currentTarget.checked)} /> Diligence findings</label>
        <label><input type="checkbox" checked={includeSuggestions} onchange={(event) => toggleInclusion('includeSuggestions', event.currentTarget.checked)} /> Audience recommendations</label>
        <label><input type="checkbox" checked={includeSmartEdits} onchange={(event) => toggleInclusion('includeSmartEdits', event.currentTarget.checked)} /> Smart Edit changes</label>
        <label><input type="checkbox" checked={includeRejected} onchange={(event) => toggleInclusion('includeRejected', event.currentTarget.checked)} /> Rejected suggestions</label>
        <div class="actions">
          <button class="button" type="button" disabled={exportStatus === 'generating'} onclick={generateExport}>
            {exportStatus === 'generating' ? 'Generating...' : 'Generate export'}
          </button>
          <span class="muted">Deck: {deckId}</span>
        </div>
        {#if exportError}
          <p class="export-error">{exportError}</p>
        {/if}
      </section>
    </div>

    <aside class="completed-panel">
      <div class="eyebrow">Export completed</div>
      <strong>Latest generated artifacts</strong>
      {#if exportRecords.length}
        {#each exportRecords as item}
          <article class="export-item">
            <div class="topline">
              <strong>{item.type}</strong>
              <span class="muted">{new Date(item.createdAt).toLocaleString()}</span>
            </div>
            {#if item.downloadUrl}
              <a class="button secondary" href={item.downloadUrl} onclick={() => trackDownload(item)}>Download export</a>
            {:else}
              <a class="button secondary" href={`/api/decks/${deckId}/exports/${item.id}/download`} onclick={() => trackDownload(item)}>Download export</a>
            {/if}
            <pre>{item.content}</pre>
          </article>
        {/each}
      {:else}
        <div class="empty-state">
          <p class="muted">No export records yet. Generate a diligence report or adapted outline to create the first review artifact.</p>
        </div>
      {/if}
    </aside>
  </div>
</section>

<style>
  .export-panel {
    padding: 1rem;
  }

  .export-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
    gap: 1rem;
  }

  .header,
  .topline,
  .actions {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .options {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1rem;
  }

  .option-button {
    display: block;
    padding: 0;
    border: 0;
    color: inherit;
    background: transparent;
    text-align: left;
    cursor: pointer;
  }

  .option-button:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 4px;
    border-radius: var(--radius-md);
  }

  .inclusion-panel,
  .completed-panel,
  .export-item {
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    padding: 1rem;
    background: rgba(255,255,255,0.03);
  }

  .inclusion-panel {
    display: grid;
    gap: 0.8rem;
  }

  .inclusion-panel label {
    display: flex;
    align-items: center;
    gap: 0.65rem;
  }

  .completed-panel {
    display: grid;
    gap: 0.9rem;
    align-content: start;
  }

  .empty-state {
    border: 1px dashed var(--line);
    border-radius: 14px;
    padding: 1rem;
  }

  .export-error {
    margin: 0;
    color: #fecaca;
  }

  pre {
    white-space: pre-wrap;
    margin: 0.8rem 0 0;
    font-family: inherit;
  }

  @media (max-width: 980px) {
    .export-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
