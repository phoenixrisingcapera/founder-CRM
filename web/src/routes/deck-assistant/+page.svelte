<script lang="ts">
  import { onMount } from 'svelte';
  import {
    createGenerationRun,
    ensureSession,
    listGenerationRuns,
    listArtifacts,
    listAudiences,
    listDecks,
    uploadDeck
  } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { ArtifactRecord, AudienceProfile, DeckGenerationRunRecord, DeckRecord } from '$lib/types';

  let audiences: AudienceProfile[] = [];
  let decks: DeckRecord[] = [];
  let artifacts: ArtifactRecord[] = [];
  let runs: DeckGenerationRunRecord[] = [];
  let selectedDeckId = '';
  let audienceCode = 'angel';
  let title = '';
  let instruction = 'Improve the narrative for investor conversations and tighten weak slides.';
  let apiKey = '';
  let provider = 'openai';
  let file: File | null = null;
  let error = '';
  let uploading = false;
  let generating = false;

  async function refresh() {
    [audiences, decks, artifacts] = await Promise.all([listAudiences(), listDecks(), listArtifacts()]);
    if (!selectedDeckId && decks.length) {
      selectedDeckId = decks[0].id;
    }
    if (audiences.length && !audiences.find((item) => item.code === audienceCode)) {
      audienceCode = audiences[0].code;
    }
    runs = selectedDeckId ? await listGenerationRuns(selectedDeckId) : [];
  }

  onMount(async () => {
    try {
      await ensureSession();
      await refresh();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load deck assistant.';
    }
  });

  async function submitUpload() {
    if (!file || !title) {
      error = 'Add a deck title and file first.';
      return;
    }
    uploading = true;
    error = '';
    try {
      const deck = await uploadDeck({ title, audience: audienceCode, file });
      title = '';
      file = null;
      selectedDeckId = deck.id;
      await refresh();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not upload deck.';
    } finally {
      uploading = false;
    }
  }

  async function submitGeneration() {
    if (!selectedDeckId) {
      error = 'Upload or select a deck first.';
      return;
    }
    generating = true;
    error = '';
    try {
      await createGenerationRun(selectedDeckId, {
        audience_code: audienceCode,
        instruction,
        api_key: apiKey || undefined,
        provider
      });
      await refresh();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not generate artifact.';
    } finally {
      generating = false;
    }
  }
</script>

<div class="page-grid">
  <SectionCard title="Deck Upload" subtitle="Upload a founder deck, extract slide content, and keep it inside the workspace.">
    <div class="form-grid">
      <input class="field" bind:value={title} placeholder="Deck title" />
      <select class="select" bind:value={audienceCode}>
        {#each audiences as audience}
          <option value={audience.code}>{audience.label}</option>
        {/each}
      </select>
      <input class="field" type="file" accept=".pdf,.txt,.md" on:change={(event) => (file = (event.currentTarget as HTMLInputElement).files?.[0] ?? null)} />
    </div>
    <div style="display:flex; justify-content:space-between; gap:1rem; align-items:center; margin-top:1rem;">
      <div class="muted">{error}</div>
      <button class="button" on:click={submitUpload} disabled={uploading}>{uploading ? 'Uploading...' : 'Upload deck'}</button>
    </div>
  </SectionCard>

  <SectionCard title="AI Deck Assistant" subtitle="Generate one investor-specific improvement artifact and save it to the workspace.">
    <div class="form-grid">
      <select class="select" bind:value={selectedDeckId}>
        <option value="">Select deck</option>
        {#each decks as deck}
          <option value={deck.id}>{deck.title}</option>
        {/each}
      </select>
      <select class="select" bind:value={audienceCode}>
        {#each audiences as audience}
          <option value={audience.code}>{audience.label}</option>
        {/each}
      </select>
      <select class="select" bind:value={provider}>
        <option value="openai">OpenAI</option>
        <option value="openrouter">OpenRouter</option>
      </select>
      <input class="field" bind:value={apiKey} placeholder="Optional OpenAI/OpenRouter API key" />
    </div>
    <textarea class="textarea" bind:value={instruction} rows="4" style="margin-top:0.75rem;" placeholder="Instruction for the assistant"></textarea>
    <div style="display:flex; justify-content:space-between; gap:1rem; align-items:center; margin-top:1rem;">
      <div class="muted">If no system key exists, the assistant uses the key you provide for this run only.</div>
      <button class="button" on:click={submitGeneration} disabled={generating}>{generating ? 'Generating...' : 'Generate artifact'}</button>
    </div>
  </SectionCard>

  <div class="cards-grid">
    <SectionCard title="Uploaded Decks" subtitle="Parsed slides are kept local to the founder workspace.">
      {#if decks.length}
        <table class="table">
          <thead><tr><th>Deck</th><th>Status</th><th>Audience</th><th>Slides</th></tr></thead>
          <tbody>
            {#each decks as deck}
              <tr><td>{deck.title}</td><td>{deck.status}</td><td>{deck.audience}</td><td>{deck.slides.length}</td></tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <EmptyState title="No deck uploaded" body="Upload a PDF, markdown file, or plain text deck to start the assistant flow." />
      {/if}
    </SectionCard>

      <SectionCard title="Generated Artifacts" subtitle="Investor-specific artifacts are stored privately and export stays off in MVP.">
      {#if artifacts.length}
        <table class="table">
          <thead><tr><th>Artifact</th><th>Export</th><th>Created</th></tr></thead>
          <tbody>
            {#each artifacts as artifact}
              <tr><td>{artifact.title}</td><td>{artifact.export_enabled ? 'Enabled' : 'Disabled'}</td><td>{new Date(artifact.created_at).toLocaleString()}</td></tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <EmptyState title="No artifact yet" body="Run the assistant once to create the first deck improvement artifact." />
      {/if}
      </SectionCard>

      <SectionCard title="Generation Runs" subtitle="Recent AI critique runs for the selected deck.">
        {#if runs.length}
          <table class="table">
            <thead><tr><th>Prompt</th><th>Provider</th><th>Status</th><th>Created</th></tr></thead>
            <tbody>
              {#each runs as run}
                <tr><td><a href={`/runs/${run.id}`}>{run.prompt_summary}</a></td><td>{run.provider} {run.model}</td><td>{run.status}</td><td>{new Date(run.created_at).toLocaleString()}</td></tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <EmptyState title="No runs yet" body="Generate a critique to create the first run record for this deck." />
        {/if}
      </SectionCard>
    </div>
  </div>
