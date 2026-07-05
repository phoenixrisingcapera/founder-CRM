<script lang="ts">
  import { onMount } from 'svelte';
  import { createOpportunity, ensureSession, listCompanies, listOpportunities, listPeople } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { CompanyRecord, OpportunityRecord, PersonRecord } from '$lib/types';

  let opportunities: OpportunityRecord[] = [];
  let companies: CompanyRecord[] = [];
  let people: PersonRecord[] = [];
  let form = { title: '', opportunity_type: 'funding', status: 'open', value_label: '', notes: '', company_id: '', person_id: '' };
  let error = '';

  async function refresh() {
    [opportunities, companies, people] = await Promise.all([listOpportunities(), listCompanies(), listPeople()]);
  }

  onMount(async () => {
    try {
      await ensureSession();
      await refresh();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load opportunities.';
    }
  });

  async function submit() {
    await createOpportunity({
      ...form,
      company_id: form.company_id || undefined,
      person_id: form.person_id || undefined
    });
    form = { title: '', opportunity_type: 'funding', status: 'open', value_label: '', notes: '', company_id: '', person_id: '' };
    await refresh();
  }
</script>

<div class="page-grid">
  <SectionCard title="Opportunities" subtitle="Track the real funding or partnership thread attached to your relationship graph.">
    <div class="form-grid">
      <input class="field" bind:value={form.title} placeholder="Opportunity title" />
      <select class="select" bind:value={form.opportunity_type}><option value="funding">Funding</option><option value="partnership">Partnership</option><option value="growth">Growth</option></select>
      <input class="field" bind:value={form.value_label} placeholder="Value label" />
      <select class="select" bind:value={form.company_id}><option value="">Select company...</option>{#each companies as company}<option value={company.id}>{company.name}</option>{/each}</select>
      <select class="select" bind:value={form.person_id}><option value="">Select person...</option>{#each people as person}<option value={person.id}>{person.name}</option>{/each}</select>
    </div>
    <textarea class="textarea" bind:value={form.notes} rows="3" placeholder="Opportunity notes" style="margin-top:0.75rem;"></textarea>
    <div style="display:flex; justify-content:space-between; margin-top:0.75rem;"><div class="muted">{error}</div><button class="button" on:click={submit} disabled={!form.title}>Add opportunity</button></div>
  </SectionCard>

  <SectionCard title="Opportunity Surface" subtitle="See active venture opportunities with linked context.">
    {#if opportunities.length}
      <table class="table">
        <thead><tr><th>Title</th><th>Type</th><th>Company</th><th>Person</th><th>Status</th><th>Value</th></tr></thead>
        <tbody>
          {#each opportunities as opportunity}
            <tr>
              <td>{opportunity.title}</td>
              <td>{opportunity.opportunity_type}</td>
              <td>{opportunity.company_name || opportunity.company_id || 'n/a'}</td>
              <td>{opportunity.person_name || opportunity.person_id || 'n/a'}</td>
              <td>{opportunity.status}</td>
              <td>{opportunity.value_label || 'n/a'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <EmptyState title="No opportunities yet" body="Track funding, partnership, and growth opportunities linked to your relationship graph." />
    {/if}
  </SectionCard>
</div>
