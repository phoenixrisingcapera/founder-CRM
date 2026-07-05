<script lang="ts">
  import { onMount } from 'svelte';
  import { createNote, createPipelineDeal, createTask, deleteNote, deletePipelineDeal, deleteTask, ensureSession, listNotes, listPeople, listPipelineDeals, listTasks, updateNote, updatePipelineDeal, updateTask } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { FollowUpTaskRecord, InteractionNoteRecord, PersonRecord, PipelineDealRecord } from '$lib/types';

  const stages = ['target investor list', 'intro requested', 'intro sent', 'first meeting', 'follow-up', 'diligence', 'soft commit', 'committed', 'passed'];

  let deals: PipelineDealRecord[] = [];
  let notes: InteractionNoteRecord[] = [];
  let tasks: FollowUpTaskRecord[] = [];
  let people: PersonRecord[] = [];
  let error = '';
  let dealForm = { name: '', stage: 'target investor list', status: 'active', target_raise_amount: '', notes: '', person_id: '' };
  let noteForm = { title: '', body: '' };
  let taskForm = { title: '', status: 'open', due_at: '' };

  async function refresh() {
    [deals, notes, tasks, people] = await Promise.all([listPipelineDeals(), listNotes(), listTasks(), listPeople()]);
  }

  onMount(async () => {
    try {
      await ensureSession();
      await refresh();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load pipeline.';
    }
  });

  async function saveDeal() {
    await createPipelineDeal({ ...dealForm, person_id: dealForm.person_id || undefined });
    dealForm = { name: '', stage: 'target investor list', status: 'active', target_raise_amount: '', notes: '', person_id: '' };
    await refresh();
  }

  async function saveNote() {
    await createNote(noteForm);
    noteForm = { title: '', body: '' };
    await refresh();
  }

  async function saveTask() {
    await createTask(taskForm);
    taskForm = { title: '', status: 'open', due_at: '' };
    await refresh();
  }

  async function editDeal(deal: PipelineDealRecord) {
    const stage = window.prompt('Update deal stage', deal.stage);
    if (stage === null) return;
    await updatePipelineDeal(deal.id, { ...deal, stage });
    await refresh();
  }

  async function removeDeal(id: string) {
    if (!window.confirm('Delete this deal?')) return;
    await deletePipelineDeal(id);
    await refresh();
  }

  async function editNote(note: InteractionNoteRecord) {
    const body = window.prompt('Update note body', note.body);
    if (body === null) return;
    await updateNote(note.id, { ...note, body });
    await refresh();
  }

  async function removeNote(id: string) {
    if (!window.confirm('Delete this note?')) return;
    await deleteNote(id);
    await refresh();
  }

  async function editTask(task: FollowUpTaskRecord) {
    const status = window.prompt('Update task status', task.status);
    if (status === null) return;
    await updateTask(task.id, { ...task, status });
    await refresh();
  }

  async function removeTask(id: string) {
    if (!window.confirm('Delete this task?')) return;
    await deleteTask(id);
    await refresh();
  }
</script>

<div class="page-grid">
  <section class="panel">
    <div class="eyebrow">Fundraising Pipeline</div>
    <h1 style="margin:0.4rem 0 0.75rem 0;">Keep the raise moving stage by stage.</h1>
    <p class="muted">{error || 'Pipeline deals, interaction notes, and follow-up tasks now sit in one workspace route.'}</p>
  </section>

  <div class="cards-grid">
    <SectionCard title="Pipeline Deals" subtitle="Track live fundraising threads.">
      <div class="form-grid">
        <input class="field" bind:value={dealForm.name} placeholder="Deal name" />
        <select class="select" bind:value={dealForm.stage}>{#each stages as stage}<option value={stage}>{stage}</option>{/each}</select>
        <input class="field" bind:value={dealForm.target_raise_amount} placeholder="Target raise amount" />
        <select class="select" bind:value={dealForm.person_id}><option value="">Select person...</option>{#each people as p}<option value={p.id}>{p.name}</option>{/each}</select>
      </div>
      <textarea class="textarea" bind:value={dealForm.notes} rows="3" placeholder="Deal notes" style="margin-top:0.75rem;"></textarea>
      <div style="display:flex; justify-content:flex-end; margin-top:0.75rem;"><button class="button" on:click={saveDeal} disabled={!dealForm.name}>Add deal</button></div>
      {#if deals.length}
        <table class="table"><thead><tr><th>Name</th><th>Stage</th><th>Person</th><th>Amount</th><th>Notes</th><th>Actions</th></tr></thead><tbody>{#each deals as deal}<tr><td>{deal.name}</td><td>{deal.stage}</td><td>{deal.person_name || deal.person_id || 'n/a'}</td><td>{deal.target_raise_amount || 'n/a'}</td><td>{deal.notes || 'No notes'}</td><td><div style="display:flex; gap:0.5rem;"><button class="button secondary" on:click={() => editDeal(deal)}>Edit</button><button class="button secondary" on:click={() => removeDeal(deal.id)}>Delete</button></div></td></tr>{/each}</tbody></table>
      {:else}
        <EmptyState title="No pipeline deals" body="Add the active raise threads you want to track across investor stages." />
      {/if}
    </SectionCard>

    <SectionCard title="Interaction Notes" subtitle="Save founder context after calls and intros.">
      <input class="field" bind:value={noteForm.title} placeholder="Note title" />
      <textarea class="textarea" bind:value={noteForm.body} rows="4" placeholder="Call summary, investor concerns, or next-step context" style="margin-top:0.75rem;"></textarea>
      <div style="display:flex; justify-content:flex-end; margin-top:0.75rem;"><button class="button" on:click={saveNote} disabled={!noteForm.title || !noteForm.body}>Add note</button></div>
      {#if notes.length}
        <table class="table"><thead><tr><th>Title</th><th>Body</th><th>Created</th><th>Actions</th></tr></thead><tbody>{#each notes as note}<tr><td>{note.title}</td><td>{note.body}</td><td>{new Date(note.created_at).toLocaleString()}</td><td><div style="display:flex; gap:0.5rem;"><button class="button secondary" on:click={() => editNote(note)}>Edit</button><button class="button secondary" on:click={() => removeNote(note.id)}>Delete</button></div></td></tr>{/each}</tbody></table>
      {:else}
        <EmptyState title="No notes yet" body="Save investor and advisor notes directly in the fundraising workspace." />
      {/if}
    </SectionCard>
  </div>

  <SectionCard title="Follow-up Tasks" subtitle="Keep the next founder action visible.">
    <div class="form-grid">
      <input class="field" bind:value={taskForm.title} placeholder="Task title" />
      <select class="select" bind:value={taskForm.status}><option value="open">Open</option><option value="queued">Queued</option><option value="done">Done</option></select>
      <input class="field" bind:value={taskForm.due_at} type="datetime-local" />
    </div>
    <div style="display:flex; justify-content:flex-end; margin-top:0.75rem;"><button class="button" on:click={saveTask} disabled={!taskForm.title}>Add task</button></div>
    {#if tasks.length}
      <table class="table"><thead><tr><th>Task</th><th>Status</th><th>Due</th><th>Actions</th></tr></thead><tbody>{#each tasks as task}<tr><td>{task.title}</td><td>{task.status}</td><td>{task.due_at ? new Date(task.due_at).toLocaleString() : 'No due date'}</td><td><div style="display:flex; gap:0.5rem;"><button class="button secondary" on:click={() => editTask(task)}>Edit</button><button class="button secondary" on:click={() => removeTask(task.id)}>Delete</button></div></td></tr>{/each}</tbody></table>
    {:else}
      <EmptyState title="No follow-up tasks" body="Add founder follow-ups so the next meeting, memo, or intro does not get lost." />
    {/if}
  </SectionCard>
</div>
