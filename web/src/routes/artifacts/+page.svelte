<script lang="ts">
  import { onMount } from 'svelte';
  import { createArtifactSignedUrl, deleteArtifact, ensureSession, listArtifacts, updateArtifactStatus } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { ArtifactRecord } from '$lib/types';

  let artifacts: ArtifactRecord[] = [];
  let error = '';

  async function loadArtifacts() {
    artifacts = await listArtifacts();
  }

  onMount(async () => {
    try {
      await ensureSession();
      await loadArtifacts();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load artifacts.';
    }
  });

  async function downloadArtifact(artifactId: string) {
    const payload = await createArtifactSignedUrl(artifactId);
    window.open(payload.download_url, '_blank', 'noopener');
  }

  async function setStatus(artifactId: string, status: string) {
    await updateArtifactStatus(artifactId, status);
    await loadArtifacts();
  }

  async function removeArtifact(artifactId: string) {
    if (!window.confirm('Delete this artifact?')) return;
    await deleteArtifact(artifactId);
    await loadArtifacts();
  }
</script>

<SectionCard title="Artifacts" subtitle="Saved AI outputs stay private to the workspace and are ready for founder review.">
  {#if error}
    <div>{error}</div>
  {:else if artifacts.length}
    <div class="page-grid">
      {#each artifacts as artifact}
        <article class="panel" style="background:#fffdf9;">
          <div style="display:flex; justify-content:space-between; gap:1rem; align-items:center;">
            <h3 style="margin:0;"><a href={`/artifacts/${artifact.id}`}>{artifact.title}</a></h3>
            <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap;">
              <span class="badge">Export {artifact.export_enabled ? 'on' : 'off'}</span>
              <button class="button secondary" on:click={() => setStatus(artifact.id, 'draft')}>Draft</button>
              <button class="button secondary" on:click={() => setStatus(artifact.id, 'approved')}>Approve</button>
              <button class="button secondary" on:click={() => setStatus(artifact.id, 'rejected')}>Reject</button>
              <button class="button secondary" on:click={() => downloadArtifact(artifact.id)}>Download</button>
              <button class="button secondary" on:click={() => removeArtifact(artifact.id)}>Delete</button>
            </div>
          </div>
          <div class="muted" style="margin-top:0.4rem;">{new Date(artifact.created_at).toLocaleString()}</div>
          <div class="muted" style="margin-top:0.4rem;">Type: {artifact.artifact_type} · Status: {artifact.artifact_status}</div>
          <pre style="white-space:pre-wrap; font-family:var(--font-body); margin:1rem 0 0 0;">{artifact.content_markdown}</pre>
        </article>
      {/each}
    </div>
  {:else}
    <EmptyState title="No artifacts saved" body="Generate a deck improvement artifact from Deck Assistant to populate this review surface." />
  {/if}
</SectionCard>
