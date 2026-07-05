<script lang="ts">
  import { onMount } from 'svelte';
  import { ensureSession, getRelationshipFit, getRelationshipGraph } from '$lib/api';
  import { session } from '$lib/stores/session';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import type { RelationshipGraphRecord, RelationshipScoreRecord } from '$lib/types';

  let graph: RelationshipGraphRecord | null = null;
  let scores: RelationshipScoreRecord[] = [];
  let goalType = 'raise_funding';
  let error = '';

  async function refresh() {
    [graph, scores] = await Promise.all([getRelationshipGraph(), getRelationshipFit(goalType)]);
  }

  onMount(async () => {
    try {
      await ensureSession();
      const ws = $session?.workspace;
      if (ws?.active_project_title) {
        goalType = ws.active_goal_type || ws.active_project_title;
      }
      await refresh();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load relationship graph.';
    }
  });
</script>

<div class="page-grid"><SectionCard title="Relationship Graph" subtitle="Visualize connections, warm paths, and network proximity."><div class="form-grid"><select class="select" bind:value={goalType} on:change={refresh}><option value="raise_funding">Raise funding</option><option value="find_advisors">Find advisors</option><option value="validate_market">Validate market</option><option value="build_operator_network">Build operator network</option></select></div><div class="muted" style="margin-top:0.75rem;">{error}</div></SectionCard>{#if graph}<SectionCard title="Graph Nodes" subtitle="Current relationship map objects."><table class="table"><thead><tr><th>Label</th><th>Kind</th></tr></thead><tbody>{#each graph.nodes as node}<tr><td>{node.label}</td><td>{node.kind}</td></tr>{/each}</tbody></table></SectionCard><SectionCard title="Goal-Based Fit Scoring" subtitle="Deterministic scoring around venture goals and signals."><table class="table"><thead><tr><th>Person</th><th>Organization</th><th>Fit</th><th>Proximity</th><th>Total</th><th>Reasons</th></tr></thead><tbody>{#each scores as score}<tr><td>{score.person_name}</td><td>{score.organization || 'n/a'}</td><td>{score.fit_score}</td><td>{score.proximity_score}</td><td>{score.total_score}</td><td>{score.reasons.join(', ')}</td></tr>{/each}</tbody></table></SectionCard>{/if}</div>
