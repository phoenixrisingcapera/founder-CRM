<script lang="ts">
  import { onMount } from 'svelte';
  import { ensureSession, getAdminFailureTickets, getAdminOverview, getAdminProviderHealth, getAdminRuns, getAdminTelemetryEvents } from '$lib/api';
  import SectionCard from '$lib/components/SectionCard.svelte';
  import type { AdminFailureTickets, AdminOverview, AdminProviderHealth, AdminRuns, AdminTelemetryEvents } from '$lib/types';

  let overview: AdminOverview | null = null;
  let telemetry: AdminTelemetryEvents | null = null;
  let failures: AdminFailureTickets | null = null;
  let providerHealth: AdminProviderHealth | null = null;
  let runs: AdminRuns | null = null;
  let error = '';

  onMount(async () => {
    try {
      await ensureSession();
      [overview, telemetry, failures, providerHealth, runs] = await Promise.all([
        getAdminOverview(),
        getAdminTelemetryEvents(),
        getAdminFailureTickets(),
        getAdminProviderHealth(),
        getAdminRuns()
      ]);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load admin visibility.';
    }
  });
</script>

{#if error}
  <div class="panel">{error}</div>
{:else if !overview || !telemetry || !failures || !providerHealth || !runs}
  <div class="panel">Loading admin visibility...</div>
{:else}
  <div class="page-grid">
    <section class="panel">
      <div class="eyebrow">Founder Ops</div>
      <h1 class="display-title" style="font-size:2.4rem;">Telemetry, failures, and AI runtime visibility.</h1>
      <p class="muted">This surface keeps fundraising execution observable without turning the founder app into a control-plane clone.</p>
    </section>

    <section class="stats-grid">
      {#each overview.summary as metric}
        <div class="panel">
          <div class="eyebrow">{metric.label}</div>
          <div style="font-size:2rem; font-weight:700; margin-top:0.35rem;">{metric.value}</div>
        </div>
      {/each}
    </section>

    <div class="cards-grid">
      <SectionCard title="Provider Health" subtitle="System and persisted user-key visibility for AI runs.">
        <table class="table">
          <thead><tr><th>Provider</th><th>Configured</th><th>Source</th></tr></thead>
          <tbody>
            {#each providerHealth.providers as provider}
              <tr><td>{provider.provider}</td><td>{provider.configured ? 'Yes' : 'No'}</td><td>{provider.source}</td></tr>
            {/each}
          </tbody>
        </table>
      </SectionCard>

      <SectionCard title="Telemetry Events" subtitle="Recent runtime events across founder CRM requests and AI flows.">
        <table class="table">
          <thead><tr><th>Event</th><th>Status</th><th>Latency</th><th>Created</th></tr></thead>
          <tbody>
            {#each telemetry.events.slice(0, 8) as event}
              <tr>
                <td>{event.event_name}<div class="muted" style="font-size:0.85rem;">{event.provider || 'system'} {event.model || ''}</div></td>
                <td>{event.status || event.event_level}</td>
                <td>{event.latency_ms ? `${event.latency_ms} ms` : 'n/a'}</td>
                <td>{new Date(event.created_at).toLocaleString()}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </SectionCard>
    </div>

    <SectionCard title="AI Runs" subtitle="Recent founder deck critique runs and saved prompt context.">
      <table class="table">
        <thead><tr><th>Run</th><th>Provider</th><th>Status</th><th>Created</th></tr></thead>
        <tbody>
          {#if runs.runs.length}
            {#each runs.runs.slice(0, 8) as run}
              <tr>
                <td>{run.prompt_summary}<div class="muted" style="font-size:0.85rem;">Deck {run.deck_id}</div></td>
                <td>{run.provider} {run.model}</td>
                <td>{run.status}</td>
                <td>{new Date(run.created_at).toLocaleString()}</td>
              </tr>
            {/each}
          {:else}
            <tr><td colspan="4" class="muted">No AI runs yet.</td></tr>
          {/if}
        </tbody>
      </table>
    </SectionCard>

    <SectionCard title="Failure Tickets" subtitle="Captured runtime failures and founder-facing issues worth triaging.">
      <table class="table">
        <thead><tr><th>Error</th><th>Route</th><th>Severity</th><th>When</th></tr></thead>
        <tbody>
          {#if failures.tickets.length}
            {#each failures.tickets as ticket}
              <tr>
                <td>{ticket.error_name || 'Error'}<div class="muted" style="font-size:0.85rem;">{ticket.error_message}</div></td>
                <td>{ticket.route || ticket.api_path || 'n/a'}</td>
                <td>{ticket.severity}</td>
                <td>{new Date(ticket.created_at).toLocaleString()}</td>
              </tr>
            {/each}
          {:else}
            <tr><td colspan="4" class="muted">No failure tickets recorded.</td></tr>
          {/if}
        </tbody>
      </table>
    </SectionCard>
  </div>
{/if}
