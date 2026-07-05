<script lang="ts">
  import { onMount } from 'svelte';
  import { ensureSession, listAiArtifacts } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { AiArtifactRecord } from '$lib/types';

  let artifacts: AiArtifactRecord[] = [];
  let error = '';

  onMount(async () => {
    try {
      await ensureSession();
      artifacts = await listAiArtifacts();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load founder briefs.';
    }
  });
</script>

<SectionCard title="Saved Briefs" subtitle="Founder-facing AI artifacts generated from scored venture contexts.">
  {#if error}
    <div>{error}</div>
  {:else if artifacts.length}
    <div class="page-grid">
      {#each artifacts as artifact}
        <article class="panel" style="background:#fffdf9;">
          <div style="display:flex; justify-content:space-between; gap:1rem; align-items:center;">
            <h3 style="margin:0;"><a href={`/artifacts/${artifact.id}`}>{artifact.title}</a></h3>
            <span class="badge">{artifact.artifact_type}</span>
          </div>
          <div class="muted" style="margin-top:0.4rem;">{artifact.project_title || artifact.project_id}</div>
          <div class="muted" style="margin-top:0.4rem;">{artifact.person_name || 'No person'} · {artifact.company_name || 'No company'} · {artifact.opportunity_title || 'No opportunity'}</div>
          <div class="muted" style="margin-top:0.4rem;">{artifact.created_at ? new Date(artifact.created_at).toLocaleString() : ''}</div>
          <pre style="white-space:pre-wrap; font-family:var(--font-body); margin:1rem 0 0 0;">{artifact.content_markdown}</pre>
        </article>
      {/each}
    </div>
  {:else}
    <EmptyState title="No founder briefs saved" body="Generate a brief from the AI Artifacts page after scoring a venture context." />
  {/if}
</SectionCard>
