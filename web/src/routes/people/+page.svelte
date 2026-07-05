<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { createDispatch, createPerson, deletePerson, ensureSession, listPeople, updatePerson } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { PersonRecord } from '$lib/types';

  let people: PersonRecord[] = [];
  let error = '';
  let saving = false;
  let form = { name: '', email: '', company: '', role: '', relationship_status: 'new', notes: '', source_kind: 'contact' };

  async function findWarmPath(personId: string) {
    goto(`/warm-path?target=${personId}`);
  }

  async function quickDispatch(person: PersonRecord) {
    await createDispatch({
      title: `Follow-up with ${person.name}`,
      person_id: person.id,
      channel: 'email',
      next_step: 'Initial outreach',
    });
    goto('/dispatches');
  }

  async function refresh() { people = await listPeople(); }

  onMount(async () => {
    try {
      await ensureSession();
      await refresh();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load people.';
    }
  });

  async function submit() {
    saving = true;
    error = '';
    try {
      await createPerson(form);
      form = { name: '', email: '', company: '', role: '', relationship_status: 'new', notes: '', source_kind: 'contact' };
      await refresh();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not save person.';
    } finally { saving = false; }
  }

  async function editPerson(person: PersonRecord) {
    const notes = window.prompt('Update notes', person.notes || '');
    if (notes === null) return;
    await updatePerson(person.id, { ...person, notes });
    await refresh();
  }

  async function removePerson(personId: string) {
    if (!window.confirm('Delete this person?')) return;
    await deletePerson(personId);
    await refresh();
  }
</script>

<div class="page-grid">
  <SectionCard title="People" subtitle="Canonical venture relationship record — merging contacts and investors in one surface.">
    <div class="form-grid">
      <input class="field" bind:value={form.name} placeholder="Full name" />
      <input class="field" bind:value={form.email} placeholder="Email" />
      <input class="field" bind:value={form.company} placeholder="Organization" />
      <input class="field" bind:value={form.role} placeholder="Role" />
      <select class="select" bind:value={form.relationship_status}>
        <option value="new">New</option>
        <option value="warm">Warm</option>
        <option value="active">Active</option>
      </select>
      <select class="select" bind:value={form.source_kind}>
        <option value="contact">Contact</option>
        <option value="investor">Investor</option>
      </select>
    </div>
    <textarea class="textarea" bind:value={form.notes} rows="3" placeholder="Relationship notes" style="margin-top:0.75rem;"></textarea>
    <div style="display:flex; justify-content:space-between; margin-top:0.75rem;">
      <div class="muted">{error}</div>
      <button class="button" on:click={submit} disabled={saving || !form.name}>{saving ? 'Saving...' : 'Add person'}</button>
    </div>
  </SectionCard>

  <SectionCard title="People Surface" subtitle="Every relationship mapped to a venture goal.">
    {#if people.length}
      <table class="table">
        <thead><tr><th>Name</th><th>Kind</th><th>Organization</th><th>Status</th><th>Notes</th><th>Actions</th></tr></thead>
        <tbody>
          {#each people as person}
            <tr>
              <td>{person.name}<div class="muted" style="font-size:0.85rem;">{person.email || ''}</div></td>
              <td>{person.source_kind}</td>
              <td>{person.company || 'n/a'}</td>
              <td>{person.relationship_status}</td>
              <td>{person.notes || 'No notes yet.'}</td>
              <td><div style="display:flex; gap:0.35rem; flex-wrap:wrap;"><button class="button secondary" on:click={() => findWarmPath(person.id)}>Warm path</button><button class="button secondary" on:click={() => quickDispatch(person)}>Dispatch</button><button class="button secondary" on:click={() => editPerson(person)}>Edit</button><button class="button secondary" on:click={() => removePerson(person.id)}>Delete</button></div></td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <EmptyState title="No people yet" body="Start mapping founders, investors, advisors, and operators around a venture goal." />
    {/if}
  </SectionCard>
</div>
