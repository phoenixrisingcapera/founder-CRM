<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { ensureSession, getGenerationRun } from '$lib/api';
  import type { DeckGenerationRunRecord } from '$lib/types';

  let run: DeckGenerationRunRecord | null = null;
  let error = '';

  onMount(async () => {
    try {
      await ensureSession();
      const runId = $page.params.runId;
      if (!runId) throw new Error('Missing run id.');
      run = await getGenerationRun(runId);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load run detail.';
    }
  });
</script>

{#if error}
  <div class="panel">{error}</div>
{:else if !run}
  <div class="panel">Loading run...</div>
{:else}
  <div class="page-grid">
    <section class="panel">
      <div class="eyebrow">Generation Run</div>
      <h1 style="margin:0.4rem 0 0.75rem 0;">{run.prompt_summary}</h1>
      <div class="muted">Deck: {run.deck_title || run.deck_id}</div>
      <div class="muted">Audience: {run.audience_label || 'n/a'}</div>
      <div class="muted">{run.provider} {run.model}</div>
      <div class="muted">Status: {run.status}</div>
      <div class="muted">Created: {new Date(run.created_at).toLocaleString()}</div>
      <div class="muted">Telemetry events: {run.telemetry_event_count}</div>
    </section>
    <section class="panel">
      <div class="eyebrow">Artifacts</div>
      {#if run.artifacts.length}
        <table class="table">
          <thead><tr><th>Title</th><th>Type</th><th>Status</th></tr></thead>
          <tbody>
            {#each run.artifacts as artifact}
              <tr><td><a href={`/artifacts/${artifact.id}`}>{artifact.title}</a></td><td>{artifact.artifact_type}</td><td>{artifact.artifact_status}</td></tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <div class="muted">No artifacts linked to this run.</div>
      {/if}
    </section>
  </div>
{/if}
