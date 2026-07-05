<script lang="ts">
  import { onMount } from 'svelte';
  import { createProject, ensureSession, listProjects } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { ProjectRecord } from '$lib/types';

  let projects: ProjectRecord[] = [];
  let form = { title: '', goal_type: 'raise_funding', status: 'active', summary: '' };
  let error = '';
  async function refresh() { projects = await listProjects(); }
  onMount(async () => { try { await ensureSession(); await refresh(); } catch (err) { error = err instanceof Error ? err.message : 'Could not load projects.'; } });
  async function submit() { await createProject(form); form = { title: '', goal_type: 'raise_funding', status: 'active', summary: '' }; await refresh(); }
</script>

<div class="page-grid"><SectionCard title="Projects" subtitle="Research-led venture operating threads."><div class="form-grid"><input class="field" bind:value={form.title} placeholder="Project title" /><select class="select" bind:value={form.goal_type}><option value="raise_funding">Raise funding</option><option value="find_advisors">Find advisors</option><option value="validate_market">Validate market</option><option value="build_operator_network">Build operator network</option></select></div><textarea class="textarea" bind:value={form.summary} rows="3" placeholder="Project summary" style="margin-top:0.75rem;"></textarea><div style="display:flex; justify-content:space-between; margin-top:0.75rem;"><div class="muted">{error}</div><button class="button" on:click={submit} disabled={!form.title}>Add project</button></div></SectionCard><SectionCard title="Project List" subtitle="Goals drive relationship mapping and workflow actions.">{#if projects.length}<table class="table"><thead><tr><th>Title</th><th>Goal</th><th>Status</th><th>Summary</th></tr></thead><tbody>{#each projects as project}<tr><td>{project.title}</td><td>{project.goal_type}</td><td>{project.status}</td><td>{project.summary || 'No summary'}</td></tr>{/each}</tbody></table>{:else}<EmptyState title="No projects yet" body="Define the venture goal first, then map relationships around it." />{/if}</SectionCard></div>
