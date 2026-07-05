<script lang="ts">
  import { onMount } from 'svelte';
  import { createCompany, deleteCompany, ensureSession, listCompanies, updateCompany } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { CompanyRecord } from '$lib/types';

  let companies: CompanyRecord[] = [];
  let error = '';
  let form = { name: '', website: '', company_type: 'target_company', sector: '', geography: '', relationship_summary: '' };

  async function refresh() { companies = await listCompanies(); }
  onMount(async () => { try { await ensureSession(); await refresh(); } catch (err) { error = err instanceof Error ? err.message : 'Could not load companies.'; } });
  async function submit() { await createCompany(form); form = { name: '', website: '', company_type: 'target_company', sector: '', geography: '', relationship_summary: '' }; await refresh(); }
  async function editCompany(company: CompanyRecord) { const summary = window.prompt('Update relationship summary', company.relationship_summary || ''); if (summary === null) return; await updateCompany(company.id, { ...company, relationship_summary: summary }); await refresh(); }
  async function removeCompany(id: string) { if (!window.confirm('Delete this company?')) return; await deleteCompany(id); await refresh(); }
</script>

<div class="page-grid">
  <SectionCard title="Companies" subtitle="Organize target companies and strategic relationships.">
    <div class="form-grid">
      <input class="field" bind:value={form.name} placeholder="Company name" />
      <input class="field" bind:value={form.website} placeholder="Website" />
      <input class="field" bind:value={form.sector} placeholder="Sector" />
      <input class="field" bind:value={form.geography} placeholder="Geography" />
    </div>
    <textarea class="textarea" bind:value={form.relationship_summary} rows="3" placeholder="Relationship summary" style="margin-top:0.75rem;"></textarea>
    <div style="display:flex; justify-content:space-between; margin-top:0.75rem;"><div class="muted">{error}</div><button class="button" on:click={submit} disabled={!form.name}>Add company</button></div>
  </SectionCard>
  <SectionCard title="Company Map" subtitle="Track strategic relationship targets.">
    {#if companies.length}
      <table class="table"><thead><tr><th>Name</th><th>Sector</th><th>Geography</th><th>Summary</th><th>Actions</th></tr></thead><tbody>{#each companies as company}<tr><td>{company.name}</td><td>{company.sector || 'n/a'}</td><td>{company.geography || 'n/a'}</td><td>{company.relationship_summary || 'No summary'}</td><td><div style="display:flex; gap:0.5rem;"><button class="button secondary" on:click={() => editCompany(company)}>Edit</button><button class="button secondary" on:click={() => removeCompany(company.id)}>Delete</button></div></td></tr>{/each}</tbody></table>
    {:else}
      <EmptyState title="No companies yet" body="Start mapping strategic companies and venture relationships." />
    {/if}
  </SectionCard>
</div>
