<script lang="ts">
  import { onMount } from 'svelte';
  import { createInvestor, deleteInvestor, ensureSession, listInvestors, updateInvestor } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { InvestorRecord } from '$lib/types';

  let investors: InvestorRecord[] = [];
  let error = '';
  let saving = false;
  let form = {
    name: '',
    investor_type: 'seed_vc',
    preferred_stage: 'seed',
    sector_relevance: '',
    thesis: '',
    check_fit_notes: '',
    warm_intro_path: '',
    risk_flags: '',
    pipeline_stage: 'target investor list'
  };

  async function loadInvestors() {
    investors = await listInvestors();
  }

  onMount(async () => {
    try {
      await ensureSession();
      await loadInvestors();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load investors.';
    }
  });

  async function submit() {
    saving = true;
    error = '';
    try {
      await createInvestor(form);
      form = {
        name: '', investor_type: 'seed_vc', preferred_stage: 'seed', sector_relevance: '', thesis: '',
        check_fit_notes: '', warm_intro_path: '', risk_flags: '', pipeline_stage: 'target investor list'
      };
      await loadInvestors();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not save investor.';
    } finally {
      saving = false;
    }
  }

  async function editInvestor(investor: InvestorRecord) {
    const thesis = window.prompt('Update investor thesis', investor.thesis || '');
    if (thesis === null) return;
    await updateInvestor(investor.id, { ...investor, thesis });
    await loadInvestors();
  }

  async function removeInvestor(investorId: string) {
    if (!window.confirm('Delete this investor?')) return;
    await deleteInvestor(investorId);
    await loadInvestors();
  }
</script>

<div class="page-grid">
  <SectionCard title="Investors" subtitle="Track fit, thesis, and pipeline movement in one founder-owned system.">
    <div class="form-grid">
      <input class="field" bind:value={form.name} placeholder="Investor or partner name" />
      <select class="select" bind:value={form.investor_type}>
        <option value="angel">Angel</option>
        <option value="seed_vc">Seed VC</option>
        <option value="series_a_vc">Series A VC</option>
        <option value="accelerator">Accelerator</option>
        <option value="strategic">Strategic</option>
      </select>
      <input class="field" bind:value={form.preferred_stage} placeholder="Preferred stage" />
      <input class="field" bind:value={form.sector_relevance} placeholder="Sector relevance" />
      <select class="select" bind:value={form.pipeline_stage}>
        <option>target investor list</option>
        <option>intro requested</option>
        <option>intro sent</option>
        <option>first meeting</option>
        <option>follow-up</option>
        <option>diligence</option>
        <option>soft commit</option>
        <option>committed</option>
        <option>passed</option>
      </select>
      <input class="field" bind:value={form.warm_intro_path} placeholder="Warm intro path" />
    </div>
    <textarea class="textarea" bind:value={form.thesis} rows="3" placeholder="Investor thesis" style="margin-top:0.75rem;"></textarea>
    <div class="form-grid" style="margin-top:0.75rem;">
      <textarea class="textarea" bind:value={form.check_fit_notes} rows="3" placeholder="Check-fit notes"></textarea>
      <textarea class="textarea" bind:value={form.risk_flags} rows="3" placeholder="Concerns or risk flags"></textarea>
    </div>
    <div style="display:flex; justify-content:space-between; gap:1rem; align-items:center; margin-top:1rem;">
      <div class="muted">{error}</div>
      <button class="button" on:click={submit} disabled={saving || !form.name}>{saving ? 'Saving...' : 'Add investor'}</button>
    </div>
  </SectionCard>

  <SectionCard title="Investor Pipeline" subtitle="The first MVP table for target list, diligence, and commit tracking.">
    {#if investors.length}
      <table class="table">
        <thead><tr><th>Name</th><th>Type</th><th>Stage</th><th>Fit</th><th>Intro Path</th><th>Risk Flags</th><th>Actions</th></tr></thead>
        <tbody>
          {#each investors as investor}
            <tr>
              <td>{investor.name}</td>
              <td>{investor.investor_type}</td>
              <td>{investor.pipeline_stage}</td>
              <td>{investor.check_fit_notes || investor.sector_relevance || 'Not assessed yet.'}</td>
              <td>{investor.warm_intro_path || 'No path captured yet.'}</td>
              <td>{investor.risk_flags || 'No flags'}</td>
              <td><div style="display:flex; gap:0.5rem;"><button class="button secondary" on:click={() => editInvestor(investor)}>Edit</button><button class="button secondary" on:click={() => removeInvestor(investor.id)}>Delete</button></div></td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <EmptyState title="No investors yet" body="Add your first target investor and track the funnel from intro requested through committed or passed." />
    {/if}
  </SectionCard>
</div>
