<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { ensureSession, getArtifact } from '$lib/api';
  import type { ArtifactDetailRecord } from '$lib/types';

  let artifact: ArtifactDetailRecord | null = null;
  let error = '';

  onMount(async () => {
    try {
      await ensureSession();
      const artifactId = $page.params.artifactId;
      if (!artifactId) throw new Error('Missing artifact id.');
      artifact = await getArtifact(artifactId);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load artifact.';
    }
  });
</script>

{#if error}
  <div class="panel">{error}</div>
{:else if !artifact}
  <div class="panel">Loading artifact...</div>
{:else}
  <div class="page-grid">
    <section class="panel">
      <div class="eyebrow">Artifact Detail</div>
      <h1 style="margin:0.4rem 0 0.75rem 0;">{artifact.title}</h1>
      <p class="muted">Deck: {artifact.deck_title || artifact.deck_id}</p>
      <p class="muted">Audience: {artifact.audience_label || 'n/a'}</p>
      <p class="muted">Type: {artifact.artifact_type}</p>
      <p class="muted">Status: {artifact.artifact_status}</p>
      <p class="muted">Run: {artifact.run?.provider} {artifact.run?.model} · {artifact.run?.status}</p>
    </section>
    {#if artifact.run}
      <section class="panel">
        <div class="eyebrow">Run Lineage</div>
        <p class="muted">Prompt: {artifact.run.prompt_summary}</p>
        <p class="muted">Telemetry events: {artifact.run.telemetry_event_count}</p>
        <p class="muted">Related artifacts: {artifact.run.artifacts.length}</p>
      </section>
    {/if}
    <section class="panel"><pre style="white-space:pre-wrap; font-family:var(--font-body); margin:0;">{artifact.content_markdown}</pre></section>
  </div>
{/if}
