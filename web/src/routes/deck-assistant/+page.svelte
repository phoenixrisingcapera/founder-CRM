<script lang="ts">
  import { onMount } from 'svelte';
  import { createGoalScore, ensureSession, generateAiArtifact, listAiArtifacts, listCompanies, listGoalScores, listOpportunities, listPeople, listProjects } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import type { AiArtifactRecord, CompanyRecord, GoalScoreRecord, OpportunityRecord, PersonRecord, ProjectRecord } from '$lib/types';

  let projects: ProjectRecord[] = [];
  let people: PersonRecord[] = [];
  let companies: CompanyRecord[] = [];
  let opportunities: OpportunityRecord[] = [];
  let scores: GoalScoreRecord[] = [];
  let artifacts: AiArtifactRecord[] = [];
  let selectedScore: GoalScoreRecord | null = null;
  let error = '';
  let scoring = false;
  let generating = false;
  let form = { project_id: '', person_id: '', company_id: '', opportunity_id: '' };
  let artifactForm = { instruction: 'Write a concise founder brief for the next investor action.', api_key: '', provider: 'openai' };

  async function refresh() {
    [projects, people, companies, opportunities, scores, artifacts] = await Promise.all([
      listProjects(),
      listPeople(),
      listCompanies(),
      listOpportunities(),
      listGoalScores(),
      listAiArtifacts()
    ]);
    if (!form.project_id && projects.length) {
      form.project_id = projects[0].id;
    }
  }

  onMount(async () => {
    try {
      await ensureSession();
      await refresh();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load AI artifacts flow.';
    }
  });

  async function scoreGoal() {
    scoring = true;
    error = '';
    try {
      selectedScore = await createGoalScore({
        project_id: form.project_id,
        person_id: form.person_id || undefined,
        company_id: form.company_id || undefined,
        opportunity_id: form.opportunity_id || undefined
      });
      await refresh();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not score this venture context.';
    } finally {
      scoring = false;
    }
  }

  async function generateBrief() {
    if (!selectedScore) {
      error = 'Score the venture context first.';
      return;
    }
    generating = true;
    error = '';
    try {
      const artifact = await generateAiArtifact({
        goal_score_id: selectedScore.id,
        project_id: selectedScore.project_id,
        person_id: selectedScore.person_id || undefined,
        company_id: selectedScore.company_id || undefined,
        opportunity_id: selectedScore.opportunity_id || undefined,
        instruction: artifactForm.instruction,
        api_key: artifactForm.api_key || undefined,
        provider: artifactForm.provider
      });
      await refresh();
      selectedScore = scores.find((item) => item.id === selectedScore?.id) || selectedScore;
      window.location.href = `/artifacts/${artifact.id}`;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not generate AI artifact.';
    } finally {
      generating = false;
    }
  }
</script>

<div class="page-grid">
  <SectionCard title="AI Artifacts" subtitle="Complete the founder demo slice: score a venture context, then save a founder brief.">
    <div class="form-grid">
      <select class="select" bind:value={form.project_id}><option value="">Select venture goal...</option>{#each projects as project}<option value={project.id}>{project.title}</option>{/each}</select>
      <select class="select" bind:value={form.person_id}><option value="">Select person...</option>{#each people as person}<option value={person.id}>{person.name}</option>{/each}</select>
      <select class="select" bind:value={form.company_id}><option value="">Select company...</option>{#each companies as company}<option value={company.id}>{company.name}</option>{/each}</select>
      <select class="select" bind:value={form.opportunity_id}><option value="">Select opportunity...</option>{#each opportunities as opportunity}<option value={opportunity.id}>{opportunity.title}</option>{/each}</select>
    </div>
    <div style="display:flex; justify-content:space-between; gap:1rem; align-items:center; margin-top:1rem;">
      <div class="muted">{error || 'Deterministic scoring runs first. AI brief generation is optional and falls back to a local founder brief if no API key is configured.'}</div>
      <button class="button" on:click={scoreGoal} disabled={scoring || !form.project_id}>{scoring ? 'Scoring...' : 'Score venture context'}</button>
    </div>
  </SectionCard>

  {#if selectedScore}
    <SectionCard title="Deterministic Score" subtitle="Relationship intelligence first, before ML.">
      <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(9rem,1fr)); gap:0.75rem; margin-bottom:1rem;">
        <div class="panel"><div class="eyebrow">Total</div><div style="font-size:2rem; font-weight:700;">{selectedScore.total_score}</div></div>
        <div class="panel"><div class="eyebrow">Relationship</div><div style="font-size:1.5rem; font-weight:700;">{selectedScore.relationship_strength_score}</div></div>
        <div class="panel"><div class="eyebrow">Warm Path</div><div style="font-size:1.5rem; font-weight:700;">{selectedScore.warm_path_score}</div></div>
        <div class="panel"><div class="eyebrow">Sector Fit</div><div style="font-size:1.5rem; font-weight:700;">{selectedScore.sector_fit_score}</div></div>
        <div class="panel"><div class="eyebrow">Stage Fit</div><div style="font-size:1.5rem; font-weight:700;">{selectedScore.stage_fit_score}</div></div>
        <div class="panel"><div class="eyebrow">Confidence</div><div style="font-size:1.5rem; font-weight:700;">{selectedScore.confidence_score}</div></div>
      </div>
      <p><strong>Recommended next action:</strong> {selectedScore.recommended_next_action}</p>
      <p class="muted"><strong>Why this score:</strong> {selectedScore.reasons.join(', ')}</p>
      <p class="muted"><strong>Missing data:</strong> {selectedScore.missing_data.length ? selectedScore.missing_data.join(', ') : 'None'}</p>

      <div class="form-grid" style="margin-top:1rem;">
        <select class="select" bind:value={artifactForm.provider}><option value="openai">OpenAI</option><option value="openrouter">OpenRouter</option></select>
        <input class="field" bind:value={artifactForm.api_key} placeholder="Optional API key" />
      </div>
      <textarea class="textarea" bind:value={artifactForm.instruction} rows="4" style="margin-top:0.75rem;" placeholder="Founder brief instruction"></textarea>
      <div style="display:flex; justify-content:flex-end; margin-top:1rem;"><button class="button" on:click={generateBrief} disabled={generating}>{generating ? 'Generating...' : 'Generate and save founder brief'}</button></div>
    </SectionCard>
  {/if}

  <div class="cards-grid">
    <SectionCard title="Recent Scores" subtitle="Saved deterministic scoring snapshots.">
      {#if scores.length}
        <table class="table">
          <thead><tr><th>Goal</th><th>Person</th><th>Score</th><th>Next Action</th></tr></thead>
          <tbody>
            {#each scores.slice(0, 6) as score}
              <tr>
                <td>{score.project_title || score.project_id}</td>
                <td>{score.person_name || score.company_name || 'n/a'}</td>
                <td><strong>{score.total_score}</strong></td>
                <td class="muted">{score.recommended_next_action}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <EmptyState title="No scores yet" body="Create your first deterministic score from a venture goal, person, company, and opportunity." />
      {/if}
    </SectionCard>

    <SectionCard title="Saved Founder Briefs" subtitle="The latest AI artifacts saved from this vertical slice.">
      {#if artifacts.length}
        <table class="table">
          <thead><tr><th>Title</th><th>Goal</th><th>Created</th></tr></thead>
          <tbody>
            {#each artifacts.slice(0, 6) as artifact}
              <tr><td><a href={`/artifacts/${artifact.id}`}>{artifact.title}</a></td><td>{artifact.project_title || artifact.project_id}</td><td>{artifact.created_at ? new Date(artifact.created_at).toLocaleString() : 'n/a'}</td></tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <EmptyState title="No founder brief yet" body="Generate and save the first founder brief after scoring a venture context." />
      {/if}
    </SectionCard>
  </div>
</div>
