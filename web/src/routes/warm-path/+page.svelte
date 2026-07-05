<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { createDispatch, ensureSession, findWarmPaths, listPeople } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { PersonRecord, WarmPathRecord } from '$lib/types';

  let people: PersonRecord[] = [];
  let paths: WarmPathRecord[] = [];
  let targetId = '';
  let loading = false;
  let error = '';
  let dispatchForm = { title: '', channel: 'intro', next_step: 'Send intro request' };

  async function refreshPeople() {
    try {
      await ensureSession();
      people = await listPeople();
      const targetParam = $page.url.searchParams.get('target');
      if (targetParam) {
        targetId = targetParam;
        await search();
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load people.';
    }
  }

  onMount(refreshPeople);

  async function search() {
    if (!targetId) return;
    loading = true;
    error = '';
    try {
      paths = await findWarmPaths(targetId);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not find warm paths.';
    } finally {
      loading = false;
    }
  }

  async function createIntroDispatch(path: WarmPathRecord) {
    await createDispatch({
      title: dispatchForm.title || `Intro: ${path.intermediary_name} → ${path.target_name}`,
      person_id: path.intermediary_person_id,
      intro_path_id: path.intro_path_id || undefined,
      channel: 'intro',
      next_step: dispatchForm.next_step,
    });
    alert(`Dispatch created for intro via ${path.intermediary_name}`);
    await search();
  }
</script>

<div class="page-grid">
  <SectionCard title="Find a Warm Path" subtitle="Pick a target investor or person and see who in your network can intro you.">
    <div class="form-grid">
      <select class="select" bind:value={targetId}>
        <option value="">Select target person...</option>
        {#each people as person}
          <option value={person.id}>{person.name} ({person.source_kind})</option>
        {/each}
      </select>
      <button class="button" on:click={search} disabled={loading || !targetId}>
        {loading ? 'Searching...' : 'Find warm paths'}
      </button>
    </div>
    <div class="muted" style="margin-top:0.75rem;">{error}</div>
  </SectionCard>

  {#if paths.length}
    <SectionCard title="Warm Paths" subtitle="Ranked intermediaries who can open the door.">
      <table class="table">
        <thead><tr><th>Intermediary</th><th>Relationship</th><th>Path</th><th>Confidence</th><th>Action</th></tr></thead>
        <tbody>
          {#each paths as path}
            <tr>
              <td><strong>{path.intermediary_name}</strong><div class="muted" style="font-size:0.85rem;">{path.intermediary_relationship_status || ''}</div></td>
              <td>{path.relationship_type}</td>
              <td class="muted">{path.path_label}</td>
              <td><span class="badge">{path.confidence}</span></td>
              <td>
                {#if path.intro_path_id}
                  <button class="button secondary" on:click={() => createIntroDispatch(path)}>Create dispatch</button>
                {:else}
                  <span class="muted">No path recorded</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </SectionCard>

    <SectionCard title="Dispatch Settings" subtitle="Set the title and next step for the intro dispatch.">
      <div class="form-grid">
        <input class="field" bind:value={dispatchForm.title} placeholder="Dispatch title (optional)" />
        <input class="field" bind:value={dispatchForm.next_step} placeholder="Next step" />
      </div>
    </SectionCard>
  {:else if targetId && !loading}
    <SectionCard title="No Warm Paths Found" subtitle="Add relationship edges or intro paths to find a connection.">
      <EmptyState title="No paths to this person yet" body="Create relationship edges between your contacts to map warm paths, or record an intro path directly." />
    </SectionCard>
  {/if}
</div>
