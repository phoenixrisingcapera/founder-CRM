<script lang="ts">
  import { onMount } from 'svelte';
  import AppShell from '$components/AppShell.svelte';

  type JsonRecord = Record<string, any>;

  let health = $state<JsonRecord | null>(null);
  let tasks = $state<JsonRecord | null>(null);
  let loading = $state(false);
  let reloading = $state(false);
  let errorMessage = $state('');

  const statusLabel = $derived(String(health?.status ?? 'unknown'));
  const packageEntries = $derived(Object.entries((health?.packages ?? {}) as JsonRecord));
  const taskEntries = $derived(Object.entries((tasks?.tasks ?? health?.tasks ?? {}) as JsonRecord));

  async function readJson(response: Response) {
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      const message =
        typeof payload?.message === 'string'
          ? payload.message
          : typeof payload?.detail === 'string'
            ? payload.detail
            : 'Request failed.';
      throw new Error(message);
    }
    return payload;
  }

  async function loadKnowledgeHealth() {
    loading = true;
    errorMessage = '';
    try {
      const [healthPayload, taskPayload] = await Promise.all([
        fetch('/api/admin/llm-knowledge/health').then(readJson),
        fetch('/api/admin/llm-knowledge/tasks').then(readJson)
      ]);
      health = healthPayload;
      tasks = taskPayload;
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Could not load LLM knowledge health.';
    } finally {
      loading = false;
    }
  }

  async function reloadKnowledge() {
    reloading = true;
    errorMessage = '';
    try {
      health = await fetch('/api/admin/llm-knowledge/reload', { method: 'POST', body: '{}' }).then(readJson);
      const taskPayload = await fetch('/api/admin/llm-knowledge/tasks').then(readJson);
      tasks = taskPayload;
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Could not reload LLM knowledge.';
    } finally {
      reloading = false;
    }
  }

  function missingModules(packageHealth: unknown) {
    if (!packageHealth || typeof packageHealth !== 'object') return [];
    const requiredModules = (packageHealth as JsonRecord).requiredModules;
    if (!requiredModules || typeof requiredModules !== 'object') return [];
    return Array.isArray(requiredModules.missing) ? requiredModules.missing : [];
  }

  onMount(() => {
    void loadKnowledgeHealth();
  });
</script>

<AppShell
  title="LLM Knowledge"
  subtitle="Runtime health for slide classification, block classification, and market verification packs."
  activeNav="admin"
  deckLabel="Knowledge Runtime"
>
  {#snippet actions()}
    <button class="button" type="button" onclick={loadKnowledgeHealth} disabled={loading || reloading}>
      {loading ? 'Checking...' : 'Refresh health'}
    </button>
    <button class="button button-secondary" type="button" onclick={reloadKnowledge} disabled={loading || reloading}>
      {reloading ? 'Reloading...' : 'Reload packs'}
    </button>
  {/snippet}

  <section class="knowledge-grid">
    <article class="panel knowledge-summary" class:knowledge-summary--degraded={statusLabel !== 'ready'}>
      <div>
        <p class="eyebrow">Runtime status</p>
        <h3>{statusLabel === 'ready' ? 'Knowledge ready' : 'Knowledge degraded'}</h3>
        <p>
          {statusLabel === 'ready'
            ? 'All required knowledge packs are available for runtime prompts.'
            : 'One or more packs are missing modules or are loading from a fallback source.'}
        </p>
      </div>
      <span>{statusLabel}</span>
    </article>

    {#if errorMessage}
      <article class="panel error-panel">
        <strong>Could not load LLM knowledge health</strong>
        <p>{errorMessage}</p>
      </article>
    {/if}

    <section class="panel">
      <div class="section-head">
        <p class="eyebrow">Knowledge packs</p>
        <h3>Pack health</h3>
      </div>

      {#if packageEntries.length === 0}
        <p class="muted">No package health reported yet.</p>
      {:else}
        <div class="package-list">
          {#each packageEntries as [packageName, packageHealth]}
            <article>
              <div class="package-row">
                <strong>{packageName}</strong>
                <span class:ready={packageHealth?.ready === true}>{packageHealth?.ready === true ? 'ready' : 'check'}</span>
              </div>
              <p>Index: {packageHealth?.indexPath ?? packageHealth?.source ?? 'not reported'}</p>
              {#if missingModules(packageHealth).length > 0}
                <small>Missing: {missingModules(packageHealth).join(', ')}</small>
              {/if}
            </article>
          {/each}
        </div>
      {/if}
    </section>

    <section class="panel">
      <div class="section-head">
        <p class="eyebrow">Task contracts</p>
        <h3>LLM task routing</h3>
      </div>

      {#if taskEntries.length === 0}
        <p class="muted">No task contracts reported yet.</p>
      {:else}
        <div class="task-list">
          {#each taskEntries as [taskName, task]}
            <article>
              <div class="package-row">
                <strong>{taskName}</strong>
                <span class:ready={task?.ready === true}>{task?.ready === true ? 'ready' : 'degraded'}</span>
              </div>
              <p>Knowledge pack: {task?.knowledgePack ?? 'not reported'}</p>
              <small>Outputs: {(task?.requiredOutputs ?? []).join(', ')}</small>
            </article>
          {/each}
        </div>
      {/if}
    </section>
  </section>
</AppShell>

<style>
  .knowledge-grid {
    display: grid;
    gap: 1rem;
  }

  .knowledge-summary {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
  }

  .knowledge-summary h3,
  .knowledge-summary p,
  .section-head h3,
  .section-head p,
  .package-list p,
  .task-list p,
  .error-panel p {
    margin: 0;
  }

  .knowledge-summary > span,
  .package-row span {
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.35rem 0.65rem;
    color: var(--success, #7fe7a6);
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
  }

  .knowledge-summary--degraded > span,
  .package-row span:not(.ready) {
    color: var(--warning, #ffd166);
  }

  .package-list,
  .task-list {
    display: grid;
    gap: 0.75rem;
  }

  .package-list article,
  .task-list article {
    display: grid;
    gap: 0.4rem;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.8rem;
    background: var(--surface-subtle);
  }

  .package-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .muted,
  .package-list p,
  .task-list p,
  .package-list small,
  .task-list small {
    color: var(--text-muted);
  }

  .error-panel {
    color: var(--danger, #ff8b8b);
  }
</style>
