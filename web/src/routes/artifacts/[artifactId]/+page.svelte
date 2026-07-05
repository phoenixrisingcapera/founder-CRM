<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { ensureSession, getAiArtifact } from '$lib/api';
  import type { AiArtifactRecord } from '$lib/types';

  let artifact: AiArtifactRecord | null = null;
  let error = '';

  onMount(async () => {
    try {
      await ensureSession();
      const artifactId = $page.params.artifactId;
      if (!artifactId) throw new Error('Missing artifact id.');
      artifact = await getAiArtifact(artifactId);
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
      <div class="eyebrow">Founder Brief</div>
      <h1 style="margin:0.4rem 0 0.75rem 0;">{artifact.title}</h1>
      <p class="muted">Goal: {artifact.project_title || artifact.project_id}</p>
      <p class="muted">Person: {artifact.person_name || 'n/a'}</p>
      <p class="muted">Company: {artifact.company_name || 'n/a'}</p>
      <p class="muted">Opportunity: {artifact.opportunity_title || 'n/a'}</p>
      <p class="muted">Type: {artifact.artifact_type}</p>
    </section>
    <section class="panel"><pre style="white-space:pre-wrap; font-family:var(--font-body); margin:0;">{artifact.content_markdown}</pre></section>
  </div>
{/if}
