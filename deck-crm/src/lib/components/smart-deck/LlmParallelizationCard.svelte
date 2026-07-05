<script lang="ts">
  import { readApiJsonOrThrow } from '$lib/api/apiError';
  import { deckProductApiPath } from '$lib/contracts';
  import { waitForWorkflowJobCompletion } from '$lib/api/deckService/workflow.client';

  interface Props {
    deckId: string;
    selectedSourceSlideIds?: string[];
    preferredModel?: string | null;
  }

  let { deckId, selectedSourceSlideIds = [], preferredModel = null }: Props = $props();

  type ParallelizationResult = {
    parallelization?: {
      taskCount?: number;
      resultCount?: number;
      partitionCount?: number;
      batchSize?: number;
      prompt?: string;
      artifactStorageKey?: string;
    };
    results?: Array<{
      taskId?: string;
      batchIndex?: number;
      slideTitles?: string[];
      slideCount?: number;
      summary?: string;
      status?: string;
    }>;
    summary?: {
      taskCount?: number;
      resultCount?: number;
      completedTaskIds?: string[];
      slideCount?: number;
    };
  };

  let prompt = $state('Create a parallel slide-by-slide LLM summary for the selected deck context.');
  let partitionCount = $state(4);
  let batchSize = $state(6);
  let model = $state('');
  let submitting = $state(false);
  let errorMessage = $state<string | null>(null);
  let acceptedJobId = $state<string | null>(null);
  let jobResult = $state<ParallelizationResult | null>(null);
  let jobStatus = $state<string | null>(null);

  const selectedCountLabel = $derived(
    selectedSourceSlideIds.length === 1 ? '1 selected slide' : `${selectedSourceSlideIds.length} selected slides`
  );

  const canSubmit = $derived(selectedSourceSlideIds.length > 0 && prompt.trim().length > 0 && !submitting);

  $effect(() => {
    if (!model && preferredModel) {
      model = preferredModel;
    }
  });

  function formatSummary(result: ParallelizationResult | null) {
    if (!result) return [];
    return (result.results ?? []).slice(0, 5).map((item) => ({
      title: item.slideTitles?.join(', ') || item.taskId || 'Batch',
      summary: item.summary ?? 'No summary returned.',
      status: item.status ?? 'completed'
    }));
  }

  async function submitParallelization() {
    if (!canSubmit) return;
    submitting = true;
    errorMessage = null;
    jobResult = null;
    acceptedJobId = null;
    jobStatus = 'queued';

    try {
      const response = await fetch(deckProductApiPath(`/decks/${deckId}/workflows/llm-parallelization`), {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        credentials: 'include',
      body: JSON.stringify({
        deckId,
        prompt: prompt.trim(),
        selectedSourceSlideIds,
        partitionCount: Number(partitionCount) || 1,
        batchSize: Number(batchSize) || 1,
        preferredModel: model.trim() || null
      })
      });
      const accepted = await readApiJsonOrThrow<Record<string, unknown>>(
        response,
        'LLM parallelization failed.',
        deckProductApiPath(`/decks/${deckId}/workflows/llm-parallelization`)
      );
      acceptedJobId = String(accepted.jobId ?? '');
      jobStatus = String(accepted.status ?? 'queued');

      if (!acceptedJobId) {
        throw new Error('LLM parallelization finished without a job id.');
      }

      const finalJob = (await waitForWorkflowJobCompletion(acceptedJobId, 'LLM parallelization failed.')) as unknown as {
        status?: string;
        output?: ParallelizationResult | null;
      };
      jobStatus = String(finalJob.status ?? 'completed');
      jobResult = finalJob.output ?? null;
    } catch (error) {
      jobStatus = 'failed';
      errorMessage = error instanceof Error ? error.message : 'LLM parallelization failed.';
    } finally {
      submitting = false;
    }
  }
</script>

<section class="panel llm-parallelization-card" aria-label="LLM parallelization">
  <header>
    <div>
      <p class="eyebrow">PySpark LLM</p>
      <h2>Parallelize the selected slides</h2>
      <p>
        Run the selected deck slices through the Spark worker in batches. This uses the new
        PySpark container and persists a workflow job you can inspect after completion.
      </p>
    </div>
    <span class="status-pill">{selectedCountLabel}</span>
  </header>

  <div class="form-grid">
    <label>
      <span>Prompt</span>
      <textarea bind:value={prompt} rows="4" placeholder="Describe the LLM task to fan out across Spark workers."></textarea>
    </label>
    <label>
      <span>Preferred model</span>
      <input bind:value={model} type="text" placeholder="optional" />
    </label>
    <label>
      <span>Partition count</span>
      <input bind:value={partitionCount} type="number" min="1" max="32" />
    </label>
    <label>
      <span>Batch size</span>
      <input bind:value={batchSize} type="number" min="1" max="64" />
    </label>
  </div>

  <div class="actions">
    <button type="button" class="button" disabled={!canSubmit} onclick={submitParallelization}>
      {#if submitting}
        Running Spark job...
      {:else}
        Run Spark parallelization
      {/if}
    </button>
    {#if acceptedJobId}
      <small>Job {acceptedJobId} · {jobStatus ?? 'queued'}</small>
    {/if}
  </div>

  {#if errorMessage}
    <p class="error">{errorMessage}</p>
  {/if}

  {#if jobResult}
    <div class="result-grid" aria-label="LLM parallelization result">
      <article>
        <span>Tasks</span>
        <strong>{jobResult.summary?.taskCount ?? jobResult.parallelization?.taskCount ?? 0}</strong>
      </article>
      <article>
        <span>Results</span>
        <strong>{jobResult.summary?.resultCount ?? jobResult.parallelization?.resultCount ?? 0}</strong>
      </article>
      <article>
        <span>Slide count</span>
        <strong>{jobResult.summary?.slideCount ?? 0}</strong>
      </article>
      <article>
        <span>Artifact</span>
        <strong>{jobResult.parallelization?.artifactStorageKey ?? 'none'}</strong>
      </article>
    </div>

    {#if formatSummary(jobResult).length > 0}
      <div class="result-list">
        {#each formatSummary(jobResult) as item}
          <article>
            <strong>{item.title}</strong>
            <p>{item.summary}</p>
            <small>{item.status}</small>
          </article>
        {/each}
      </div>
    {/if}
  {/if}
</section>

<style>
  .llm-parallelization-card {
    display: grid;
    gap: 0.9rem;
    margin-bottom: 1rem;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
    background: var(--surface);
  }

  .llm-parallelization-card header {
    display: flex;
    gap: 1rem;
    justify-content: space-between;
    align-items: start;
  }

  .llm-parallelization-card h2,
  .llm-parallelization-card p {
    margin: 0;
  }

  .llm-parallelization-card .eyebrow,
  .llm-parallelization-card small,
  .llm-parallelization-card label span,
  .llm-parallelization-card .status-pill,
  .llm-parallelization-card .error {
    color: var(--text-muted);
  }

  .status-pill {
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.35rem 0.65rem;
    background: var(--surface-subtle);
    white-space: nowrap;
  }

  .form-grid {
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  }

  label {
    display: grid;
    gap: 0.4rem;
  }

  textarea,
  input {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.7rem 0.8rem;
    background: var(--surface-subtle);
    color: var(--text);
  }

  .actions {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .error {
    margin: 0;
    color: #ef4444;
  }

  .result-grid,
  .result-list {
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }

  .result-grid article,
  .result-list article {
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.75rem;
    background: var(--surface-subtle);
    min-width: 0;
  }

  .result-grid span,
  .result-list p,
  .result-list small {
    color: var(--text-muted);
  }

  .result-list p {
    margin: 0.2rem 0 0.4rem;
  }
</style>
