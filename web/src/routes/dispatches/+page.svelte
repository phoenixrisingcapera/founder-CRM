<script lang="ts">
  import { onMount } from 'svelte';
  import { createDispatch, ensureSession, listDispatches } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { DispatchRecord } from '$lib/types';

  let dispatches: DispatchRecord[] = [];
  let form = { title: '', channel: 'email', status: 'draft', next_step: '', project_id: '', person_id: '', intro_path_id: '' };
  let error = '';
  async function refresh() { dispatches = await listDispatches(); }
  onMount(async () => { try { await ensureSession(); await refresh(); } catch (err) { error = err instanceof Error ? err.message : 'Could not load dispatches.'; } });
  async function submit() {
    const p = { ...form, project_id: form.project_id || undefined, person_id: form.person_id || undefined, intro_path_id: form.intro_path_id || undefined };
    await createDispatch(p); form = { title: '', channel: 'email', status: 'draft', next_step: '', project_id: '', person_id: '', intro_path_id: '' }; await refresh();
  }
</script>

<div class="page-grid"><SectionCard title="Dispatches" subtitle="Create outbound plans, follow-ups, and relationship actions."><div class="form-grid"><input class="field" bind:value={form.title} placeholder="Dispatch title" /><select class="select" bind:value={form.channel}><option value="email">Email</option><option value="intro">Intro</option><option value="meeting">Meeting</option></select><input class="field" bind:value={form.project_id} placeholder="Project ID (optional)" /><input class="field" bind:value={form.person_id} placeholder="Person ID (optional)" /><input class="field" bind:value={form.intro_path_id} placeholder="Intro path ID (optional)" /><input class="field" bind:value={form.next_step} placeholder="Next step" /></div><div style="display:flex; justify-content:space-between; margin-top:0.75rem;"><div class="muted">{error}</div><button class="button" on:click={submit} disabled={!form.title}>Add dispatch</button></div></SectionCard><SectionCard title="Dispatch Queue" subtitle="Relationship-synced outbound actions.">{#if dispatches.length}<table class="table"><thead><tr><th>Title</th><th>Channel</th><th>Person</th><th>Project</th><th>Intro Path</th><th>Status</th><th>Next Step</th></tr></thead><tbody>{#each dispatches as dispatch}<tr><td>{dispatch.title}</td><td>{dispatch.channel}</td><td>{dispatch.person_name || dispatch.person_id || 'n/a'}</td><td>{dispatch.project_title || dispatch.project_id || 'n/a'}</td><td>{dispatch.intro_path_label || dispatch.intro_path_id || 'n/a'}</td><td>{dispatch.status}</td><td>{dispatch.next_step || 'No next step'}</td></tr>{/each}</tbody></table>{:else}<EmptyState title="No dispatches yet" body="Create the outbound plan that moves the next relationship forward." />{/if}</SectionCard></div>
