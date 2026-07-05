<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { AdminAgentTeam } from '$lib/types/admin';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  let selectedTeamKey = $state<string | null>(null);

  const teams = $derived(data.agentTeams.teams);
  const selectedTeam = $derived(teams.find((team) => team.key === selectedTeamKey) ?? teams[0] ?? null);
  const summaryCards = $derived([
    { label: 'Agent teams', value: data.agentTeams.summary.teamCount, detail: 'Bounded templates' },
    { label: 'Observed runs', value: data.agentTeams.summary.observedRuns, detail: 'Recent admin feed' },
    { label: 'Running', value: data.agentTeams.summary.runningRuns, detail: 'Active handoffs' },
    { label: 'Failed', value: data.agentTeams.summary.failedRuns, detail: 'Needs review' }
  ]);

  function label(value: string | null | undefined) {
    return value?.replaceAll('_', ' ').replaceAll(':', ' / ') ?? 'Unknown';
  }

  function formatDate(value: string | null) {
    if (!value) return 'n/a';
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(value));
  }

  function teamTone(team: AdminAgentTeam) {
    return team.status === 'observed' ? 'observed' : 'planned';
  }
</script>

<AppShell
  title="Agent Teams"
  subtitle="Multi-agent coordination map for bounded Deck AIStack workflows and handoff ownership."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="teams-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a class="active" href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/elements">Elements</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
    </nav>

    <section class="summary-grid" aria-label="Agent team summary">
      {#each summaryCards as card}
        <article class="panel summary-card">
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.detail}</small>
        </article>
      {/each}
    </section>

    <section class="principles panel" aria-label="Coordination principles">
      {#each data.agentTeams.principles as principle}
        <p>{principle}</p>
      {/each}
    </section>

    <section class="teams-layout">
      <article class="panel team-list-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Templates</p>
            <h2>Coordinated workflows</h2>
          </div>
        </div>
        <div class="team-list">
          {#each teams as team}
            <button
              class:active={selectedTeam?.key === team.key}
              class="team-row"
              type="button"
              onclick={() => (selectedTeamKey = team.key)}
            >
              <span class={`status ${teamTone(team)}`}>{label(team.status)}</span>
              <strong>{team.name}</strong>
              <small>{team.observedRunCount} observed runs</small>
              <p>{team.purpose}</p>
            </button>
          {/each}
        </div>
      </article>

      <article class="panel team-detail-panel">
        {#if selectedTeam}
          <div class="panel-head">
            <div>
              <p class="eyebrow">Team detail</p>
              <h2>{selectedTeam.name}</h2>
            </div>
            <span class={`status ${teamTone(selectedTeam)}`}>{label(selectedTeam.status)}</span>
          </div>

          <section class="roles-grid" aria-label="Agent roles">
            {#each selectedTeam.roles as role}
              <article class="role-card">
                <span>{label(role.status)}</span>
                <strong>{role.name}</strong>
                <p>{role.responsibility}</p>
              </article>
            {/each}
          </section>

          <section class="handoff-section" aria-label="Handoff boundaries">
            <h3>Handoffs</h3>
            <ol>
              {#each selectedTeam.handoffs as handoff}
                <li>{handoff}</li>
              {/each}
            </ol>
          </section>

          <section class="handoff-section" aria-label="Recent matching runs">
            <h3>Recent matching runs</h3>
            <div class="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Deck</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {#each selectedTeam.recentRuns as run}
                    <tr>
                      <td><a href={`/admin/agents/${encodeURIComponent(run.id)}`}>{run.id}</a></td>
                      <td>{label(run.runType)}</td>
                      <td><span class="status neutral">{label(run.status)}</span></td>
                      <td>{run.deckTitle ?? run.deckId ?? 'No deck'}</td>
                      <td>{formatDate(run.updatedAt)}</td>
                    </tr>
                  {:else}
                    <tr>
                      <td colspan="5" class="empty">No recent runs match this team template yet.</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </section>
        {:else}
          <p class="muted">No agent team templates are configured.</p>
        {/if}
      </article>
    </section>
  </section>
</AppShell>

<style>
  /* Hallmark · macrostructure: Workbench · tone: utilitarian · anchor hue: cyan */
  .teams-page,
  .teams-layout {
    display: grid;
    gap: 1rem;
  }

  .admin-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .admin-tabs a {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.55rem 0.75rem;
    color: var(--text-muted);
    text-decoration: none;
    background: var(--surface-subtle);
  }

  .admin-tabs a.active {
    color: var(--text);
    border-color: var(--accent);
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.85rem;
  }

  .summary-card,
  .principles,
  .team-list-panel,
  .team-detail-panel {
    padding: 1rem;
  }

  .summary-card {
    display: grid;
    gap: 0.4rem;
  }

  .summary-card span,
  .summary-card small,
  .team-row small,
  .team-row p,
  .role-card span,
  .role-card p {
    color: var(--text-muted);
  }

  .summary-card strong {
    font-size: 1.8rem;
  }

  .principles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.75rem;
  }

  .principles p {
    margin: 0;
    color: var(--text-muted);
  }

  .teams-layout {
    grid-template-columns: minmax(280px, 0.42fr) minmax(0, 1fr);
    align-items: start;
  }

  .panel-head {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
    margin-bottom: 1rem;
  }

  .panel-head h2,
  .panel-head p {
    margin: 0;
  }

  .team-list {
    display: grid;
    gap: 0.6rem;
  }

  .team-row {
    display: grid;
    grid-template-columns: 100px minmax(0, 1fr);
    gap: 0.35rem 0.75rem;
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    color: inherit;
    padding: 0.75rem;
    text-align: left;
    cursor: pointer;
  }

  .team-row.active {
    border-color: var(--accent);
  }

  .team-row small,
  .team-row p {
    grid-column: 2;
    margin: 0;
  }

  .status {
    display: inline-flex;
    width: fit-content;
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.22rem 0.5rem;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .status.observed {
    border-color: rgba(52, 211, 153, 0.45);
    color: #bbf7d0;
  }

  .status.planned {
    border-color: rgba(250, 204, 21, 0.45);
    color: #fde68a;
  }

  .roles-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.75rem;
  }

  .role-card {
    display: grid;
    gap: 0.35rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-subtle);
    padding: 0.75rem;
  }

  .role-card p {
    margin: 0;
  }

  .handoff-section {
    margin-top: 1.25rem;
  }

  .handoff-section h3 {
    margin: 0 0 0.75rem;
  }

  ol {
    display: grid;
    gap: 0.5rem;
    margin: 0;
    padding-left: 1.2rem;
    color: var(--text-muted);
  }

  .table-scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    min-width: 760px;
    border-collapse: collapse;
    font-size: 0.82rem;
  }

  th,
  td {
    border-top: 1px solid var(--border);
    padding: 0.55rem 0.5rem;
    text-align: left;
    vertical-align: top;
  }

  th {
    color: var(--text-muted);
    font-weight: 600;
  }

  td a {
    color: #bae6fd;
  }

  .empty {
    color: var(--text-muted);
    text-align: center;
  }

  @media (max-width: 980px) {
    .teams-layout {
      grid-template-columns: 1fr;
    }

    .team-row {
      grid-template-columns: 1fr;
    }

    .team-row small,
    .team-row p {
      grid-column: 1;
    }
  }
</style>
