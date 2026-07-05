<script lang="ts">
  import { deckProductApiPath } from '$lib/contracts';
  import { goto } from '$app/navigation';
  import type { DesignBatchPreview } from '@deck-aistack-codes/shared';
  import AppShell from '$components/AppShell.svelte';
  import type { DeckGraph } from '$types/domain';
  import { sessionState } from '$lib/stores/session';
  import DeckVisualizerSurface from '$components/smart-deck/DeckVisualizerSurface.svelte';

  type DueDiligenceDomain = {
    key: string;
    label: string;
    score: number;
    status: string;
    findings: string[];
  };

  type DueDiligenceClaim = {
    id: string;
    claimText: string;
    claimType: string;
    slideId?: string | null;
    slideTitle?: string | null;
    evidenceStatus: string;
    riskLevel: 'low' | 'medium' | 'high';
    confidence: number;
    recommendedAction: string;
  };

  type DueDiligenceAudienceFit = {
    audience: string;
    fitScore: number;
    strengths: string[];
    weaknesses: string[];
    likelyQuestions: string[];
  };

  type DueDiligenceIcmemo = {
    thesis: string;
    reasonsToBelieve: string[];
    mainRisks: string[];
    recommendation: string;
  };

  type DueDiligenceLpView = {
    fundReturnPotential: 'low' | 'medium' | 'high';
    portfolioFit: 'low' | 'medium' | 'strong' | 'high';
    followOnReservePressure: 'low' | 'medium' | 'high';
    exitPathwayClarity: 'low' | 'medium' | 'high';
    concern?: string | null;
  };

  type DueDiligenceRiskItem = {
    risk: string;
    category: string;
    severity: 'low' | 'medium' | 'high';
    evidence: string;
    mitigation: string;
  };

  type DueDiligenceWorkspace = {
    deckId: string;
    runId: string | null;
    analysisRunCount?: number;
    latestAnalysisRunAt?: string | null;
    recentAnalysisRuns?: { id: string; status: string; createdAt?: string; created_at?: string }[];
    status: string;
    selectedAudience: string;
    summary: {
      investment_readiness_score: number;
      evidence_quality: string;
      market_claim_risk: string;
      ic_readiness: string;
      lp_suitability: string;
    };
    domains: DueDiligenceDomain[];
    claims: DueDiligenceClaim[];
    audienceFit: DueDiligenceAudienceFit;
    icMemo: DueDiligenceIcmemo;
    lpView: DueDiligenceLpView;
    riskRegister: DueDiligenceRiskItem[];
    diligenceWorkspace?: Record<string, unknown> | null;
    knowledgeMetadata?: {
      name?: string | null;
      version?: string | null;
      source?: string | null;
    } | null;
  };

  type PageData = {
    graph: DeckGraph;
    latestBatches: DesignBatchPreview[];
    diligenceWorkspace: DueDiligenceWorkspace | null;
    selectedAudience: string | null;
  };

  const audienceOptions = [
    { value: 'seed_vc', label: 'Seed VC' },
    { value: 'series_a_vc', label: 'Series A VC' },
    { value: 'growth_equity', label: 'Growth Equity' },
    { value: 'angel', label: 'Angel' },
    { value: 'corporate', label: 'Corporate Venture' },
    { value: 'lp', label: 'LP' },
    { value: 'investment_committee', label: 'Investment Committee' },
    { value: 'family_office', label: 'Family Office' },
    { value: 'fund_partner', label: 'Fund Partner' },
    { value: 'institutional', label: 'Institutional' }
  ] as const;

  let { data }: { data: PageData } = $props();
  const selectedAudience = $derived(data.selectedAudience);
  const diligenceWorkspace = $derived(data.diligenceWorkspace);
  const deck = $derived(data.graph.deck);
  let workspace = $state<DueDiligenceWorkspace | null>(null);
  let audience = $state('seed_vc');
  let statusMessage = $state('Run diligence review');
  let isAudienceLoading = $state(false);
  let isRunning = $state(false);
  const evidenceSlideId = $derived(workspace?.claims?.find((claim) => claim.slideId)?.slideId ?? null);
  const evidenceSlide = $derived(
    evidenceSlideId ? data.graph.slides.find((slide) => slide.id === evidenceSlideId) ?? data.graph.slides[0] ?? null : data.graph.slides[0] ?? null
  );
  const canExport = $derived(
    $sessionState.status === 'authenticated' && $sessionState.permissions.includes('deck:export')
  );
  const exportStatus = $derived(canExport ? 'Enabled' : 'Disabled');

  const cards = $derived<{ title: string; value: string; note: string }[]>([
    { title: 'Investment Readiness', value: `${workspace?.summary?.investment_readiness_score ?? 0} / 100`, note: 'Readiness signal' },
    { title: 'Evidence Quality', value: workspace?.summary?.evidence_quality ?? 'n/a', note: 'Claim strength' },
    { title: 'Market Claim Risk', value: workspace?.summary?.market_claim_risk ?? 'n/a', note: 'Market sourcing' },
    { title: 'IC Readiness', value: workspace?.summary?.ic_readiness ?? 'needs_review', note: 'Partner-ready path' },
    { title: 'LP Suitability', value: workspace?.summary?.lp_suitability ?? 'n/a', note: 'Portfolio fit view' },
    {
      title: 'Export Status',
      value: exportStatus,
      note: canExport ? 'Export path available from action bar' : 'Enable with deck export permission'
    }
  ]);

  const topAudience = $derived(audienceLabel(audience));
  const hasLpAudience = $derived(
    ['lp', 'investment_committee', 'family_office', 'fund_partner', 'institutional'].includes(audience)
  );
  const actionLabel = $derived(isAudienceLoading || isRunning ? 'Running...' : statusMessage);

  $effect(() => {
    const nextWorkspace = normalizeWorkspace(diligenceWorkspace);
    workspace = nextWorkspace;

    if (selectedAudience) {
      audience = selectedAudience;
    } else if (nextWorkspace?.selectedAudience) {
      audience = nextWorkspace.selectedAudience;
    } else if (!audience) {
      audience = 'seed_vc';
    }
    syncAudienceQuery(audience);
  });

  function syncAudienceQuery(nextAudience: string) {
    if (typeof window === 'undefined') return;
    const current = new URL(window.location.href);
    if (nextAudience) {
      current.searchParams.set('audience', nextAudience);
    } else {
      current.searchParams.delete('audience');
    }
    window.history.replaceState({}, '', `${current.pathname}${current.search}`);
  }

  function audienceLabel(value: string) {
    const mapping: Record<string, string> = audienceOptions.reduce(
      (acc, item) => {
        acc[item.value] = item.label;
        return acc;
      },
      {} as Record<string, string>
    );
    return mapping[value] || value;
  }

  function toStringArray(value: unknown): string[] {
    if (!Array.isArray(value)) return [];
    return value.map((item) => (typeof item === 'string' ? item : String(item)));
  }

  function toNumber(value: unknown): number | null {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value === 'string' && value.trim()) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  }

  function normalizeAudienceFit(raw: unknown): DueDiligenceAudienceFit {
    const source = (raw ?? {}) as Record<string, unknown>;
    return {
      audience: String((source.audience as string | undefined) ?? source.audienceFit ?? ''),
      fitScore: toNumber(source.fitScore) ?? toNumber(source.fit_score) ?? 0,
      strengths: toStringArray(source.strengths),
      weaknesses: toStringArray(source.weaknesses),
      likelyQuestions: toStringArray(source.likelyQuestions).length
        ? toStringArray(source.likelyQuestions)
        : toStringArray(source.likely_questions)
    };
  }

  function normalizeIcmemo(raw: unknown): DueDiligenceIcmemo {
    const source = (raw ?? {}) as Record<string, unknown>;
    return {
      thesis: String((source.thesis as string | undefined) ?? ''),
      reasonsToBelieve: toStringArray(source.reasonsToBelieve).length
        ? toStringArray(source.reasonsToBelieve)
        : toStringArray(source.reasons_to_believe),
      mainRisks: toStringArray(source.mainRisks).length ? toStringArray(source.mainRisks) : toStringArray(source.main_risks),
      recommendation: String((source.recommendation as string | undefined) ?? 'needs_review')
    };
  }

  function normalizeLpView(raw: unknown): DueDiligenceLpView {
    const source = (raw ?? {}) as Record<string, unknown>;
    return {
      fundReturnPotential: String(
        (source.fundReturnPotential as string | undefined) ??
          (source.fund_return_potential as string | undefined) ??
          'medium'
      ) as DueDiligenceLpView['fundReturnPotential'],
      portfolioFit: String(
        (source.portfolioFit as string | undefined) ??
          (source.portfolio_fit as string | undefined) ??
          'medium'
      ) as DueDiligenceLpView['portfolioFit'],
      followOnReservePressure: String(
        (source.followOnReservePressure as string | undefined) ??
          (source.follow_on_reserve_pressure as string | undefined) ??
          'medium'
      ) as DueDiligenceLpView['followOnReservePressure'],
      exitPathwayClarity: String(
        (source.exitPathwayClarity as string | undefined) ??
          (source.exit_pathway_clarity as string | undefined) ??
          'low'
      ) as DueDiligenceLpView['exitPathwayClarity'],
      concern: (source.concern as string | null | undefined) ?? null
    };
  }

  function normalizeClaim(raw: unknown): DueDiligenceClaim {
    const source = (raw ?? {}) as Record<string, unknown>;
    return {
      id: String((source.id as string | undefined) ?? ''),
      claimText: String(
        (source.claimText as string | undefined) ??
          (source.claim_text as string | undefined) ??
          ''
      ),
      claimType: String(
        (source.claimType as string | undefined) ??
          (source.claim_type as string | undefined) ??
          'evidence_gap'
      ),
      slideId:
        (source.slideId as string | null | undefined) ??
        (source.slide_id as string | undefined) ??
        null,
      slideTitle:
        (source.slideTitle as string | null | undefined) ??
        (source.slide_title as string | undefined) ??
        null,
      evidenceStatus: String(
        (source.evidenceStatus as string | undefined) ??
          (source.evidence_status as string | undefined) ??
          'missing'
      ),
      riskLevel: (String(
        (source.riskLevel as string | undefined) ??
          (source.risk_level as string | undefined) ??
          'low'
      ) as DueDiligenceClaim['riskLevel']),
      confidence: toNumber(source.confidence) ?? 0.45,
      recommendedAction: String(
        (source.recommendedAction as string | undefined) ??
          (source.recommended_action as string | undefined) ??
          'verify'
      )
    };
  }

  function normalizeRisk(raw: unknown): DueDiligenceRiskItem {
    const source = (raw ?? {}) as Record<string, unknown>;
    return {
      risk: String((source.risk as string | undefined) ?? ''),
      category: String((source.category as string | undefined) ?? ''),
      severity: (String(
        (source.severity as string | undefined) ?? 'low'
      ) as DueDiligenceRiskItem['severity']),
      evidence: String((source.evidence as string | undefined) ?? ''),
      mitigation: String((source.mitigation as string | undefined) ?? '')
    };
  }

  function normalizeWorkspace(raw: DueDiligenceWorkspace | null | undefined): DueDiligenceWorkspace | null {
    if (!raw) {
      return {
        deckId: deck.id,
        runId: null,
        status: 'not_ready',
        selectedAudience: audience,
        summary: {
          investment_readiness_score: 0,
          evidence_quality: 'n/a',
          market_claim_risk: 'n/a',
          ic_readiness: 'needs_review',
          lp_suitability: 'n/a'
        },
        domains: [],
        claims: [],
        audienceFit: {
          audience,
          fitScore: 0,
          strengths: [],
          weaknesses: [],
          likelyQuestions: []
        },
        icMemo: {
          thesis: 'No IC memo yet.',
          reasonsToBelieve: [],
          mainRisks: [],
          recommendation: 'needs_review'
        },
        lpView: {
          fundReturnPotential: 'medium',
          portfolioFit: 'medium',
          followOnReservePressure: 'medium',
          exitPathwayClarity: 'low'
        },
        riskRegister: []
      };
    }

    return {
      deckId: (raw as { deckId?: string; deck_id?: string }).deckId ?? (raw as { deckId?: string; deck_id?: string }).deck_id ?? deck.id,
      runId: (raw as { runId?: string | null; run_id?: string | null }).runId ?? (raw as { runId?: string | null; run_id?: string | null }).run_id ?? null,
      status: raw.status,
      selectedAudience:
        (raw as { selectedAudience?: string; selected_audience?: string }).selectedAudience ??
        (raw as { selectedAudience?: string; selected_audience?: string }).selected_audience ??
        audience,
      summary: raw.summary,
      domains: raw.domains || [],
      claims: ((raw as { claims?: unknown[]; }).claims ?? []).map((item) => normalizeClaim(item)),
      audienceFit:
        normalizeAudienceFit(
          (raw as { audienceFit?: unknown; audience_fit?: unknown }).audienceFit ??
            (raw as { audienceFit?: unknown; audience_fit?: unknown }).audience_fit ??
            { audience: raw.selectedAudience || audience }
        ),
      icMemo:
        normalizeIcmemo(
          (raw as { icMemo?: unknown; ic_memo?: unknown }).icMemo ??
            (raw as { icMemo?: unknown; ic_memo?: unknown }).ic_memo ??
            {
              thesis: 'No IC memo yet.',
              reasonsToBelieve: [],
              mainRisks: [],
              recommendation: 'needs_review'
            }
        ),
      lpView:
        normalizeLpView(
          (raw as { lpView?: unknown; lp_view?: unknown }).lpView ??
            (raw as { lpView?: unknown; lp_view?: unknown }).lp_view ?? {
              fund_return_potential: 'medium',
              portfolio_fit: 'medium',
              follow_on_reserve_pressure: 'medium',
              exit_pathway_clarity: 'low'
            }
        ),
      riskRegister:
        (((raw as { riskRegister?: unknown[]; risk_register?: unknown[] }).riskRegister ??
          (raw as { riskRegister?: unknown[]; risk_register?: unknown[] }).risk_register ??
          []) as unknown[]).map((item) => normalizeRisk(item)),
      diligenceWorkspace:
        (raw as { diligenceWorkspace?: Record<string, unknown> | null; diligence_workspace?: Record<string, unknown> | null })
          .diligenceWorkspace ??
        (raw as { diligenceWorkspace?: Record<string, unknown> | null; diligence_workspace?: Record<string, unknown> | null })
          .diligence_workspace ??
        null,
      knowledgeMetadata:
        (raw as {
          knowledgeMetadata?: Record<string, unknown> | null;
          knowledge_metadata?: Record<string, unknown> | null;
        }).knowledgeMetadata ??
        (raw as {
          knowledgeMetadata?: Record<string, unknown> | null;
          knowledge_metadata?: Record<string, unknown> | null;
        }).knowledge_metadata ??
        null
    };
  }

  function setAudience(nextAudience: string) {
    audience = nextAudience;
    syncAudienceQuery(nextAudience);
    void loadWorkspace(nextAudience);
  }

  async function runDiligence() {
    isRunning = true;
    statusMessage = 'Running due diligence analysis...';
    try {
      const response = await fetch(deckProductApiPath(`/decks/${deck.id}/due-diligence`), {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          audience,
          runMode: 'full_review',
          run_mode: 'full_review'
        })
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        const message = typeof payload?.message === 'string' ? payload.message : 'Due diligence run failed.';
        throw new Error(message);
      }
      const payload = (await response.json()) as DueDiligenceWorkspace;
      workspace = normalizeWorkspace(payload);
      audience = payload.selectedAudience || audience;
      statusMessage = 'Run complete';
    } catch (err) {
      statusMessage = err instanceof Error ? err.message : 'Failed to run due diligence.';
    } finally {
      isRunning = false;
      window.setTimeout(() => {
        statusMessage = 'Run diligence review';
      }, 1600);
    }
  }

  async function loadWorkspace(nextAudience: string) {
    isAudienceLoading = true;
    try {
      const response = await fetch(
        deckProductApiPath(`/decks/${deck.id}/due-diligence?audience=${encodeURIComponent(nextAudience)}`)
      );
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        const message = typeof payload?.message === 'string' ? payload.message : 'Could not load workspace.';
        throw new Error(message);
      }
      const payload = (await response.json()) as DueDiligenceWorkspace;
      workspace = normalizeWorkspace(payload);
      audience = payload.selectedAudience || nextAudience;
      statusMessage = 'Run diligence review';
    } catch (err) {
      statusMessage = err instanceof Error ? err.message : 'Could not load workspace.';
    } finally {
      isAudienceLoading = false;
    }
  }
</script>

  <AppShell
    title="Due diligence"
  subtitle="Persistent workspace for deck evidence, risks, and review cards."
  status={deck.status}
  deckLabel={deck.title}
  currentDeckId={deck.id}
  latestBatches={data.latestBatches}
  activeNav="diligence"
>
  {#snippet actions()}
    <a class="button secondary" href={`/decks/${deck.id}/smart-edit`}>Smart Edit</a>
    {#if canExport}
      <a class="button" href={`/decks/${deck.id}/export`}>Export</a>
    {:else}
      <button class="button" disabled title="Export requires deck:export permission">Export</button>
    {/if}
  {/snippet}

  <section class="due-diligence-page" aria-label="Due diligence workspace">
    <header class="due-diligence-page__top">
      <div>
        <p class="eyebrow">Due Diligence Workspace</p>
        <h1>Investor control room</h1>
        <p class="muted">Run a structured review, inspect claim risks, and route edits.</p>
      </div>
      <div class="audience-control">
        <label for="audience">Audience lens</label>
        <select id="audience" bind:value={audience} onchange={(event) => setAudience((event.target as HTMLSelectElement).value)}>
          {#each audienceOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </div>
      <button class="button" type="button" onclick={runDiligence} disabled={isRunning || isAudienceLoading}>
        {actionLabel}
      </button>
    </header>

    <div class="summary-grid">
      {#each cards as card}
        <article class="panel summary-card">
          <span>{card.title}</span>
          <strong>{card.value}</strong>
          <small>{card.note}</small>
        </article>
      {/each}
    </div>

    <div class="due-diligence-page__primary">
      <div class="due-diligence-page__main">
        <DeckVisualizerSurface
          title="Due diligence visualizer"
          subtitle="Shared slide surface for evidence review and deck inspection."
          slide={evidenceSlide}
          emptyTitle="No evidence slide loaded"
          emptyText="Run diligence to resolve a claim-backed slide preview."
        />

        <section class="panel">
          <div class="card-head">
            <h2>Diligence domains</h2>
            <small>Audience: {topAudience}</small>
          </div>
          <div class="domain-list">
            {#if workspace?.domains?.length}
              {#each workspace.domains as domain}
                <article class="panel due-diligence-slot">
                  <div class="eyebrow">{domain.label}</div>
                  <div class="domain-score">{Math.round(domain.score)} / 100</div>
                  <div>{domain.status}</div>
                  <ul>
                    {#each domain.findings.slice(0, 3) as finding}
                      <li>{finding}</li>
                    {/each}
                  </ul>
                </article>
              {/each}
            {:else}
              <p class="muted">No domain results yet. Run due diligence to populate this workspace.</p>
            {/if}
          </div>
        </section>

        <section class="panel">
          <div class="card-head">
            <h2>Claim evidence table</h2>
            <small>{workspace?.claims?.length ?? 0} findings</small>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Claim</th>
                  <th>Type</th>
                  <th>Slide</th>
                  <th>Evidence</th>
                  <th>Risk</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {#if workspace?.claims?.length}
                  {#each workspace.claims as claim}
                    <tr>
                      <td>{claim.claimText}</td>
                      <td>{claim.claimType}</td>
                      <td>{claim.slideTitle ?? claim.slideId ?? '-'}</td>
                      <td>{claim.evidenceStatus}</td>
                      <td>{claim.riskLevel}</td>
                      <td>{claim.recommendedAction}</td>
                    </tr>
                  {/each}
                {:else}
                  <tr>
                    <td colspan="6" class="muted">No findings reported for this workspace.</td>
                  </tr>
                {/if}
              </tbody>
            </table>
          </div>
        </section>

        <div class="dual-cards">
          <section class="panel">
            <h2>Audience fit</h2>
            <p class="muted">Audience: {workspace?.audienceFit?.audience ?? topAudience}</p>
            <p><strong>Fit score:</strong> {workspace?.audienceFit?.fitScore ?? '--'}</p>
            <div>
              <div class="eyebrow">Strong points</div>
              <ul>
                {#each workspace?.audienceFit?.strengths ?? [] as item}
                  <li>{item}</li>
                {/each}
              </ul>
            </div>
            <div>
              <div class="eyebrow">Weak points</div>
              <ul>
                {#each workspace?.audienceFit?.weaknesses ?? [] as item}
                  <li>{item}</li>
                {/each}
              </ul>
            </div>
          </section>

          <section class="panel">
            <h2>IC memo preview</h2>
            <p>{workspace?.icMemo?.thesis ?? 'No IC memo yet.'}</p>
            <div>
              <div class="eyebrow">Main risks</div>
              <ul>
                {#each workspace?.icMemo?.mainRisks ?? [] as risk}
                  <li>{risk}</li>
                {/each}
              </ul>
            </div>
            <p><strong>Recommendation:</strong> {workspace?.icMemo?.recommendation ?? '—'}</p>
          </section>
        </div>

        <section class="panel">
          <h2>Risk register</h2>
          <div class="risk-grid">
            {#if workspace?.riskRegister?.length}
              {#each workspace.riskRegister as risk}
                <article class="risk-item panel">
                  <h3>{risk.risk}</h3>
                  <p>{risk.evidence}</p>
                  <p><strong>Mitigation:</strong> {risk.mitigation}</p>
                  <small>{risk.category} • {risk.severity}</small>
                </article>
              {/each}
            {:else}
              <p class="muted">No risks identified yet.</p>
            {/if}
          </div>
        </section>
      </div>

      <aside class="due-diligence-page__cards" aria-label="Due diligence action cards">
        <section class="panel due-diligence-slot">
          <div>
            <div class="eyebrow">Selected audience</div>
            <h2>{topAudience}</h2>
            <p>{workspace?.summary?.evidence_quality ?? 'No workspace data loaded yet.'}</p>
          </div>
          <p><strong>Deck:</strong> {deck.title}</p>
          <p><strong>Run:</strong> {workspace?.runId ?? 'Not run in this session'}</p>
          <p><strong>Run history:</strong> {workspace?.analysisRunCount ?? 0} analyses</p>
          <p><strong>Last analysis:</strong> {workspace?.latestAnalysisRunAt ? new Date(workspace.latestAnalysisRunAt).toLocaleString() : 'Not available'}</p>
          <div>
            <div class="eyebrow">Recent runs</div>
            <ul>
              {#each workspace?.recentAnalysisRuns ?? [] as item}
                <li>{new Date(item.createdAt ?? item.created_at ?? '').toLocaleString()} - {item.status}</li>
              {/each}
              {#if !(workspace?.recentAnalysisRuns?.length)}
                <li class="muted">No recent runs captured yet.</li>
              {/if}
            </ul>
          </div>
          <button class="button secondary" type="button" onclick={() => void goto(`/decks/${deck.id}/smart-edit`)}>
            Open Smart Edit
          </button>
          <button class="button" type="button" onclick={() => void loadWorkspace('investment_committee')}>
            Generate IC-ready view
          </button>

          {#if hasLpAudience}
            <div class="panel due-diligence-slot">
              <div class="eyebrow">LP view</div>
              <p>Fund return potential: <strong>{workspace?.lpView?.fundReturnPotential ?? '--'}</strong></p>
              <p>Portfolio fit: <strong>{workspace?.lpView?.portfolioFit ?? '--'}</strong></p>
              <p>Reserve pressure: <strong>{workspace?.lpView?.followOnReservePressure ?? '--'}</strong></p>
              <p>Exit clarity: <strong>{workspace?.lpView?.exitPathwayClarity ?? '--'}</strong></p>
              {#if workspace?.lpView?.concern}
                <p><strong>Concern:</strong> {workspace.lpView.concern}</p>
              {/if}
            </div>
          {:else}
            <div class="panel due-diligence-slot">
              <div class="eyebrow">LP view</div>
              <p>Available for LP / IC lenses.</p>
            </div>
          {/if}
        </section>

        <section class="panel due-diligence-slot">
          <div>
            <div class="eyebrow">Deck knowledge</div>
            <h2>{workspace?.knowledgeMetadata?.name ?? 'diligence-pack'}</h2>
          </div>
          <p><strong>Version:</strong> {workspace?.knowledgeMetadata?.version ?? 'local runtime'}</p>
          <p><strong>Source:</strong> {workspace?.knowledgeMetadata?.source ?? 'backend'}</p>
        </section>
      </aside>
    </div>
  </section>
</AppShell>

<style>
  .due-diligence-page {
    display: grid;
    gap: 1rem;
  }

  .due-diligence-page__top {
    display: grid;
    gap: 0.8rem;
    grid-template-columns: minmax(0, 1fr) 260px auto;
    align-items: end;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.8rem;
  }

  .summary-card {
    padding: 0.85rem;
  }

  .summary-card strong {
    display: block;
    font-size: 1.35rem;
  }

  .due-diligence-page__primary {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(260px, 35%);
    gap: 1rem;
    align-items: start;
  }

  .due-diligence-page__main {
    min-width: 0;
    display: grid;
    gap: 1rem;
  }

  .due-diligence-page__cards {
    display: grid;
    gap: 0.75rem;
    min-width: 0;
  }

  .panel {
    border-radius: 10px;
    padding: 1rem;
  }

  .card-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }

  .domain-list {
    display: grid;
    gap: 0.8rem;
    margin-top: 0.8rem;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  }

  .domain-score {
    font-weight: 700;
    margin-bottom: 0.35rem;
  }

  .due-diligence-slot {
    min-height: 140px;
    display: grid;
    gap: 0.5rem;
  }

  .dual-cards {
    display: grid;
    gap: 0.8rem;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .risk-grid {
    display: grid;
    gap: 0.8rem;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  }

  .risk-item h3,
  .risk-item p {
    margin: 0;
  }

  .table-wrap {
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    border-bottom: 1px solid var(--border);
    padding: 0.65rem;
    text-align: left;
    vertical-align: top;
  }

  .audience-control {
    display: grid;
    gap: 0.3rem;
  }

  @media (max-width: 1200px) {
    .due-diligence-page__top {
      grid-template-columns: 1fr;
      align-items: start;
    }

    .summary-grid,
    .dual-cards {
      grid-template-columns: 1fr;
    }

    .due-diligence-page__primary {
      grid-template-columns: 1fr;
    }
  }
</style>
