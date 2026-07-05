<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { activateProject, deactivateProject, ensureSession, getDashboard, getRelationshipFit, listDispatches, listOpportunities, listProjects } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { DashboardSummary, DispatchRecord, OpportunityRecord, ProjectRecord, RelationshipScoreRecord } from '$lib/types';

  let summary: DashboardSummary | null = null;
  let scores: RelationshipScoreRecord[] = [];
  let projects: ProjectRecord[] = [];
  let dispatches: DispatchRecord[] = [];
  let opportunities: OpportunityRecord[] = [];
  let error = '';

  async function refresh() {
    const goal = summary?.active_goal_type || 'raise_funding';
    [summary, scores, projects, dispatches, opportunities] = await Promise.all([
      getDashboard(),
      getRelationshipFit(goal),
      listProjects(),
      listDispatches(),
      listOpportunities(),
    ]);
  }

  onMount(async () => {
    try {
      await ensureSession();
      await refresh();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load the dashboard.';
    }
  });

  async function setActiveProject(projectId: string) {
    await activateProject(projectId);
    await refresh();
  }

  async function clearActiveProject() {
    await deactivateProject();
    await refresh();
  }
</script>

{#if error}
  <div class="panel">{error}</div>
{:else if !summary}
  <div class="panel">Loading dashboard...</div>
{:else}
  <div class="page-grid">
    <section class="panel">
      <div class="eyebrow">Founder Workspace</div>
      <h1 class="display-title">Venture relationship intelligence, not a generic CRM.</h1>
      <p class="muted" style="max-width:52rem;">Map relationships, run dispatches, track opportunities, and move your raise forward — all anchored to your venture goals.</p>
      <div style="display:flex; gap:0.75rem; flex-wrap:wrap; margin-top:1rem;">
        {#if summary.active_project_title}
          <span class="badge" style="background:#166534;color:#fff;">Active goal: {summary.active_project_title}</span>
          <button class="button secondary" on:click={() => goto('/warm-path')}>Find warm paths</button>
          <button class="button secondary" on:click={clearActiveProject}>Clear</button>
        {:else}
          <span class="badge">No active goal — set one below</span>
        {/if}
        <span class="badge">Deck readiness: {summary.deck_readiness_score}%</span>
        <span class="badge">People mapped: {summary.metrics.find(m => m.label === 'People')?.value || 0}</span>
      </div>
    </section>

    <section class="stats-grid">
      {#each summary.metrics as metric}
        <div class="panel">
          <div class="eyebrow">{metric.label}</div>
          <div style="font-size:2rem; font-weight:700; margin-top:0.35rem;">{metric.value}</div>
        </div>
      {/each}
    </section>

    <div class="cards-grid">
      {#if summary.suggested_actions.length}
        <SectionCard title="Suggested Actions" subtitle="Highest-fit people needing a move.">
          <table class="table">
            <thead><tr><th>Person</th><th>Score</th><th>Suggested Action</th><th>Intro Paths</th><th>Act</th></tr></thead>
            <tbody>
              {#each summary.suggested_actions as action}
                <tr>
                  <td>{action.person_name}</td>
                  <td><strong>{action.total_score}%</strong></td>
                  <td class="muted">{action.suggested_action}</td>
                  <td>{action.intro_paths_available > 0 ? `${action.intro_paths_available} available` : 'None'}</td>
                  <td><button class="button secondary" on:click={() => goto(`/warm-path?target=${action.person_id}`)}>Warm path</button></td>
                </tr>
              {/each}
            </tbody>
          </table>
        </SectionCard>
      {/if}

      <SectionCard title="Highest Relationship Fit" subtitle="Top-ranked people for your active goal.">
        {#if scores.length}
          <table class="table">
            <thead><tr><th>Person</th><th>Fit</th><th>Proximity</th><th>Total</th><th>Reasons</th></tr></thead>
            <tbody>
              {#each scores.slice(0, 5) as score}
                <tr>
                  <td>{score.person_name}</td>
                  <td>{score.fit_score}%</td>
                  <td>{score.proximity_score}%</td>
                  <td><strong>{score.total_score}%</strong></td>
                  <td class="muted">{score.reasons.join(', ')}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <EmptyState title="No relationship scores yet" body="Add people to see their relationship fit ranked by venture goal." />
        {/if}
      </SectionCard>

      <SectionCard title="Active Projects" subtitle="Set the active goal to orient your dashboard.">
        {#if projects.length}
          <table class="table">
            <thead><tr><th>Project</th><th>Goal</th><th>Status</th><th>Activate</th></tr></thead>
            <tbody>
              {#each projects as project}
                <tr>
                  <td>{project.title}</td>
                  <td>{project.goal_type}</td>
                  <td>{project.status}</td>
                  <td>
                    {#if summary.active_project_id === project.id}
                      <span class="badge" style="background:#166534;color:#fff;">Active</span>
                    {:else}
                      <button class="button secondary" on:click={() => setActiveProject(project.id)}>Set active</button>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <EmptyState title="No projects yet" body="Define the venture goal first, then map relationships around it." />
        {/if}
      </SectionCard>

      <SectionCard title="Recent Dispatches" subtitle="Outbound plans moving relationships forward.">
        {#if dispatches.length}
          <table class="table">
            <thead><tr><th>Dispatch</th><th>Person</th><th>Status</th></tr></thead>
            <tbody>
              {#each dispatches.slice(0, 4) as dispatch}
                <tr><td>{dispatch.title}</td><td>{dispatch.person_name || dispatch.person_id || 'n/a'}</td><td>{dispatch.status}</td></tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <EmptyState title="No dispatches yet" body="Create the outbound plan that moves the next relationship forward." />
        {/if}
      </SectionCard>

      <SectionCard title="Open Opportunities" subtitle="Funding, partnership, and growth chances.">
        {#if opportunities.length}
          <table class="table">
            <thead><tr><th>Opportunity</th><th>Type</th><th>Status</th></tr></thead>
            <tbody>
              {#each opportunities.slice(0, 4) as opp}
                <tr><td>{opp.title}</td><td>{opp.opportunity_type}</td><td>{opp.status}</td></tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <EmptyState title="No opportunities yet" body="Track funding, partnership, and growth opportunities here." />
        {/if}
      </SectionCard>
    </div>
  </div>
{/if}
