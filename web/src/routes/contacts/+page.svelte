<script lang="ts">
  import { onMount } from 'svelte';
  import { createContact, deleteContact, ensureSession, listContacts, updateContact } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { ContactRecord } from '$lib/types';

  let contacts: ContactRecord[] = [];
  let error = '';
  let saving = false;
  let form = {
    name: '',
    email: '',
    company: '',
    role: '',
    contact_type: 'advisor',
    relationship_status: 'new',
    notes: ''
  };

  async function loadContacts() {
    contacts = await listContacts();
  }

  onMount(async () => {
    try {
      await ensureSession();
      await loadContacts();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load contacts.';
    }
  });

  async function submit() {
    saving = true;
    error = '';
    try {
      await createContact(form);
      form = { name: '', email: '', company: '', role: '', contact_type: 'advisor', relationship_status: 'new', notes: '' };
      await loadContacts();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not save contact.';
    } finally {
      saving = false;
    }
  }

  async function editContact(contact: ContactRecord) {
    const notes = window.prompt('Update contact notes', contact.notes || '');
    if (notes === null) return;
    await updateContact(contact.id, { ...contact, notes });
    await loadContacts();
  }

  async function removeContact(contactId: string) {
    if (!window.confirm('Delete this contact?')) return;
    await deleteContact(contactId);
    await loadContacts();
  }
</script>

<div class="page-grid">
  <SectionCard title="Contacts" subtitle="Advisors, angels, operators, and every warm path around your raise.">
    <div class="form-grid">
      <input class="field" bind:value={form.name} placeholder="Full name" />
      <input class="field" bind:value={form.email} placeholder="Email" />
      <input class="field" bind:value={form.company} placeholder="Organization" />
      <input class="field" bind:value={form.role} placeholder="Role" />
      <select class="select" bind:value={form.contact_type}>
        <option value="advisor">Advisor</option>
        <option value="angel">Angel</option>
        <option value="accelerator">Accelerator</option>
        <option value="operator">Operator</option>
      </select>
      <select class="select" bind:value={form.relationship_status}>
        <option value="new">New</option>
        <option value="warm">Warm</option>
        <option value="active">Active</option>
      </select>
    </div>
    <textarea class="textarea" bind:value={form.notes} rows="4" placeholder="Relationship notes, warm intro context, and founder-specific history." style="margin-top:0.75rem;"></textarea>
    <div style="display:flex; justify-content:space-between; gap:1rem; align-items:center; margin-top:1rem;">
      <div class="muted">{error}</div>
      <button class="button" on:click={submit} disabled={saving || !form.name}>{saving ? 'Saving...' : 'Add contact'}</button>
    </div>
  </SectionCard>

  <SectionCard title="Relationship Table" subtitle="Clean contact history for founders, not generic lead scoring clutter.">
    {#if contacts.length}
      <table class="table">
        <thead><tr><th>Name</th><th>Role</th><th>Organization</th><th>Type</th><th>Status</th><th>Notes</th><th>Actions</th></tr></thead>
        <tbody>
          {#each contacts as contact}
            <tr>
              <td>{contact.name}<div class="muted" style="font-size:0.85rem;">{contact.email || ''}</div></td>
              <td>{contact.role || 'n/a'}</td>
              <td>{contact.company || 'n/a'}</td>
              <td>{contact.contact_type}</td>
              <td>{contact.relationship_status}</td>
              <td>{contact.notes || 'No notes yet.'}</td>
              <td><div style="display:flex; gap:0.5rem;"><button class="button secondary" on:click={() => editContact(contact)}>Edit</button><button class="button secondary" on:click={() => removeContact(contact.id)}>Delete</button></div></td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <EmptyState title="No contacts yet" body="Start with the people who can open investor doors or sharpen the raise narrative." />
    {/if}
  </SectionCard>
</div>
