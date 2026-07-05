<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { BlockClassification, DeckSlide, DeckSlideBlock, SmartEditSuggestion } from '$types/domain';
  import type { PageData } from './$types';
  import DeckVisualizerSurface from '$components/smart-deck/DeckVisualizerSurface.svelte';

  type AudienceType =
    | 'vc_investor'
    | 'angel_investor'
    | 'investment_committee'
    | 'corporate_venture'
    | 'grant_funder'
    | 'accelerator'
    | 'acquirer'
    | 'strategic_partner';

  type SmartEditRequest = {
    slide_id: string;
    block_id: string;
    instruction: string;
    audience_type: AudienceType;
  };

  type SmartEditResponse = {
    run: {
      id: string;
      deck_id: string;
      slide_id: string;
      block_id: string;
      instruction: string;
      audience_type: AudienceType;
      created_at: string;
    };
    suggestion: {
      id: string;
      run_id: string;
      deck_id: string;
      slide_id: string;
      block_id: string;
      original_text: string;
      suggested_text: string;
      reason: string;
      risk_level: 'low' | 'medium' | 'high';
      status: 'pending' | 'accepted' | 'rejected' | 'edited' | 'applied';
    };
  };

  type SuggestionPatchRequest = {
    status: 'accepted' | 'rejected' | 'edited' | 'applied';
    edited_text?: string | null;
    finalText?: string | null;
  };

  async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(path, init);
    if (!response.ok) {
      throw new Error(await response.text());
    }
    return (await response.json()) as T;
  }

  function createSmartEdit(deckId: string, body: SmartEditRequest) {
    return requestJson<SmartEditResponse>(`/api/decks/${deckId}/smart-edit`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body)
    });
  }

  function patchSmartEditSuggestion(deckId: string, suggestionId: string, body: SuggestionPatchRequest) {
    return requestJson<{ suggestion: SmartEditResponse['suggestion'] }>(`/api/decks/${deckId}/suggestions/${suggestionId}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body)
    });
  }

  type EditableFieldView = {
    fieldKey: string;
    slideId?: string;
    blockId?: string;
    label?: string;
    usageSummary?: string;
  };

  type SelectedFieldView = {
    fieldKey: string;
    label?: string;
    value?: string;
  };

  let { data }: { data: PageData } = $props();
  const defaultInstruction = 'Make this more precise and suitable for an Investment Committee.';
  let instruction = $state('');
  let instructionInitialized = $state(false);
  let activeSuggestion = $state<SmartEditSuggestion | null>(null);
  let smartEditStatus = $state<'idle' | 'generating' | 'saving' | 'saved' | 'failed'>('idle');
  let smartEditError = $state('');

  $effect(() => {
    if (instructionInitialized) return;
    instruction = data.initialInstruction ?? defaultInstruction;
    instructionInitialized = true;
  });

  const selectedSlide = $derived(data.graph.slides.find((slide) => slide.id === data.selectedSlideId) ?? data.graph.slides[0]);
  const blocks = $derived(data.graph.blocks.filter((block) => block.slideId === selectedSlide?.id));
  const selectedBlock = $derived(data.graph.blocks.find((block) => block.id === data.selectedBlockId));
  const selectedClassification = $derived(
    selectedBlock ? data.graph.classifications.find((item) => item.blockId === selectedBlock.id) : undefined
  );
  const selectedSuggestion = $derived(
    activeSuggestion && selectedBlock && activeSuggestion.blockId === selectedBlock.id
      ? activeSuggestion
      : selectedBlock
      ? [...data.graph.smartEditSuggestions].reverse().find((suggestion) => suggestion.blockId === selectedBlock.id)
      : data.graph.smartEditSuggestions[data.graph.smartEditSuggestions.length - 1]
  );
  const selectedField = $derived(((data as PageData & { selectedField?: SelectedFieldView | null }).selectedField ?? null) as
    | SelectedFieldView
    | null);
  const editableFields = $derived(
    Array.isArray((data as PageData & { editableFields?: EditableFieldView[] }).editableFields)
      ? ((data as PageData & { editableFields?: EditableFieldView[] }).editableFields as EditableFieldView[])
      : []
  );

  function slideHref(slideId: string, blockId?: string) {
    const params = new URLSearchParams({ slide: slideId });
    if (blockId) params.set('block', blockId);
    return `/decks/${data.graph.deck.id}/smart-edit?${params.toString()}`;
  }

  function editableFieldHref(field: EditableFieldView) {
    const targetSlideId = field.slideId ?? selectedSlide?.id;
    if (field.blockId && targetSlideId) {
      return slideHref(targetSlideId, field.blockId);
    }
    if (targetSlideId) {
      return slideHref(targetSlideId);
    }
    return `/decks/${data.graph.deck.id}/smart-edit`;
  }

  function classificationFor(blockId: string) {
    return data.graph.classifications.find((item) => item.blockId === blockId);
  }

  function riskLevelFrom(classification?: BlockClassification) {
    if (!classification) return 'informational';
    if (classification.diligenceCategory === 'evidence') return 'high';
    if (classification.diligenceCategory === 'market') return 'medium';
    return 'low';
  }

  function chipsFor(block: DeckSlideBlock, classification?: BlockClassification) {
    return [classification?.semanticTag, block.blockType, classification?.diligenceCategory].filter(Boolean) as string[];
  }

  function slideTone(slide: DeckSlide) {
    const map: Record<string, string> = {
      cover: 'tone-cover',
      problem: 'tone-problem',
      market: 'tone-market',
      solution: 'tone-solution',
      product: 'tone-product',
      traction: 'tone-traction',
      business_model: 'tone-model',
      team: 'tone-team'
    };
    return map[slide.role] ?? 'tone-default';
  }

  function displaySuggestion(suggestion?: SmartEditSuggestion) {
    if (!suggestion) return null;
    return {
      title: 'AI suggestion',
      text: suggestion.suggestedText,
      reason: suggestion.reason,
      status: suggestion.status,
      generated: 'Generated just now'
    };
  }

  function mapSmartEditSuggestion(suggestion: SmartEditResponse['suggestion']): SmartEditSuggestion {
    return {
      id: suggestion.id,
      runId: suggestion.run_id,
      deckId: suggestion.deck_id,
      slideId: suggestion.slide_id,
      blockId: suggestion.block_id,
      originalText: suggestion.original_text,
      suggestedText: suggestion.suggested_text,
      reason: suggestion.reason,
      riskLevel: suggestion.risk_level,
      status: suggestion.status
    };
  }

  async function generateSmartEditSuggestion() {
    if (!selectedSlide || !selectedBlock) return;
    const trimmedInstruction = instruction.trim();
    if (!trimmedInstruction) {
      smartEditStatus = 'failed';
      smartEditError = 'Add an instruction before generating a Smart Edit suggestion.';
      return;
    }

    smartEditStatus = 'generating';
    smartEditError = '';
    try {
      const response = await createSmartEdit(data.graph.deck.id, {
        slide_id: selectedSlide.id,
        block_id: selectedBlock.id,
        instruction: trimmedInstruction,
        audience_type: 'investment_committee'
      });
      activeSuggestion = mapSmartEditSuggestion(response.suggestion);
      smartEditStatus = 'saved';
    } catch (error) {
      smartEditStatus = 'failed';
      smartEditError = error instanceof Error ? error.message : 'Smart Edit generation failed.';
    }
  }

  async function decideSmartEditSuggestion(status: 'accepted' | 'rejected') {
    const suggestion = selectedSuggestion;
    if (!suggestion) return;

    smartEditStatus = 'saving';
    smartEditError = '';
    try {
      const response = await patchSmartEditSuggestion(data.graph.deck.id, suggestion.id, { status });
      activeSuggestion = mapSmartEditSuggestion(response.suggestion);
      smartEditStatus = 'saved';
    } catch (error) {
      smartEditStatus = 'failed';
      smartEditError = error instanceof Error ? error.message : `Smart Edit suggestion could not be ${status}.`;
    }
  }
</script>

<AppShell
  title="Smart Edit"
  subtitle="Block-level AI editing for diligence decks. Suggestions remain reviewable before any applied revision."
  status={data.graph.deck.status}
  deckLabel={data.graph.deck.title}
  currentDeckId={data.graph.deck.id}
  latestBatches={data.latestBatches}
  activeNav="smart-edit"
>
  {#snippet actions()}
    <span class="saved-pill">All changes saved</span>
    <a class="button secondary" href={`/decks/${data.graph.deck.id}/smart-deck`}>View in Workspace</a>
    <a class="button secondary" href={`/decks/${data.graph.deck.id}/due-diligence`}>Due Diligence Adapter</a>
    <a class="button" href={`/decks/${data.graph.deck.id}/export`}>Export</a>
  {/snippet}

  <section class="workspace-full">
    <div class="smart-edit-shell editor-viewport">
    <aside class="panel slide-rail">
      <div class="rail-top">
        <div>
          <div class="eyebrow">Slides</div>
          <h2>{data.graph.slides.length} slides</h2>
        </div>
      </div>

      <div class="search-row">
        <input type="search" placeholder="Search slides..." />
        <button type="button" class="icon-filter" aria-label="Filter slides">+</button>
      </div>

      <div class="slide-stack">
        {#each data.graph.slides as slide}
          <a class:selected={slide.id === selectedSlide?.id} class="slide-item" href={slideHref(slide.id)}>
            <div class={`slide-thumb ${slideTone(slide)}`}>
              <div class="mini-line wide"></div>
              <div class="mini-line"></div>
              <div class="mini-dot"></div>
            </div>

            <div class="slide-copy">
              <div class="slide-meta">
                <strong>{String(slide.slideIndex).padStart(2, '0')}</strong>
                <span>{slide.title}</span>
              </div>
              <small>{slide.role.replace('_', ' ')}</small>
            </div>
          </a>
        {/each}
      </div>

      <button type="button" class="add-slide">+ Add slide</button>
    </aside>

    <section class="panel workspace-panel">
      <div class="breadcrumbs">
        <a href="/decks">Decks</a>
        <span>/</span>
        <a href={`/decks/${data.graph.deck.id}/smart-deck`}>{data.graph.deck.title}</a>
        <span>/</span>
        <strong>Smart Edit</strong>
      </div>

      <div class="workspace-head">
        <div>
          <h2>Slide {String(selectedSlide?.slideIndex ?? 0).padStart(2, '0')}: {selectedSlide?.title}</h2>
          <div class="context-row">
            <span class="context-chip">Audience: {data.graph.deck.audience}</span>
            <span class="context-chip">Purpose: {data.graph.deck.purpose}</span>
          </div>
        </div>
        <span class="role-pill">{selectedSlide?.role}</span>
      </div>

      <DeckVisualizerSurface
        title="Smart Edit visualizer"
        subtitle="Shared slide surface reused by Smart Deck, Smart Edit, and Due Diligence."
        slide={selectedSlide}
        emptyTitle="Select a slide"
        emptyText="Choose a slide from the left rail to load the shared visualizer surface."
      />

      <div class="tab-row">
        <span class="tab muted">Slide View</span>
        <span class="tab active">Blocks <strong>{blocks.length}</strong></span>
      </div>

      <div class="block-stack">
        {#each blocks as block}
          {@const classification = classificationFor(block.id)}
          <a class:selected={block.id === selectedBlock?.id} class="block-card" href={slideHref(selectedSlide.id, block.id)}>
            <div class="block-top">
              <div class="block-index">{block.blockIndex + 1}</div>
              <div>
                <strong>{block.blockType}</strong>
                <p>{block.rawText}</p>
              </div>
              <button type="button" class="dots" aria-label="Block actions">⋮</button>
            </div>

            <div class="chip-row">
              {#each chipsFor(block, classification) as chip}
                <span class="chip">{chip}</span>
              {/each}
              {#if classification}
                <span class="confidence">Confidence {classification.confidence.toFixed(2)}</span>
              {/if}
            </div>
          </a>
        {/each}
      </div>

      <div class="footer-row">
        <span>{blocks.length} blocks on this slide</span>
        <div class="risk-scale">
          <span class="risk high">High risk</span>
          <span class="risk medium">Medium risk</span>
          <span class="risk low">Low risk</span>
          <span class="risk info">Informational</span>
        </div>
      </div>
    </section>

    <aside class="panel insight-panel">
      <div class="insight-group">
        <div class="section-head">
          <strong>Selected Block</strong>
          {#if selectedBlock}
            <a href={slideHref(selectedSlide.id)}>Change Block</a>
          {/if}
        </div>
        <div class="card">
          {#if selectedBlock}
            <p class="block-label">Block {selectedBlock.blockIndex + 1} • {selectedBlock.blockType}</p>
            <p>{selectedBlock.rawText}</p>
          {:else}
            <p class="muted">Select a block from the center workspace to inspect classification and generate a reviewable suggestion.</p>
          {/if}
        </div>
      </div>

      <div class="insight-group">
        <div class="section-head">
          <strong>Editable fields</strong>
          <span class="muted">{editableFields.length} loaded</span>
        </div>
        <div class="card">
          <div class="field-list">
            {#each editableFields.slice(0, 5) as field}
              <a
                class:active={field.fieldKey === data.selectedFieldKey}
                class="field-chip"
                href={editableFieldHref(field)}
              >
                <strong>{field.label}</strong>
                <small>{field.usageSummary}</small>
              </a>
            {/each}
          </div>
          {#if selectedField}
            <div class="selected-field">
              <strong>{selectedField.label}</strong>
              <p>{selectedField.value}</p>
              <small>{selectedField.fieldKey}</small>
            </div>
          {/if}
        </div>
      </div>

      <div class="insight-group">
        <div class="section-head">
          <strong>Classification</strong>
          <a href={`/decks/${data.graph.deck.id}/smart-deck`}>Why?</a>
        </div>
        <div class="card classification-card">
          {#if selectedClassification}
            <dl>
              <div>
                <dt>Semantic tag</dt>
                <dd>{selectedClassification.semanticTag}</dd>
              </div>
              <div>
                <dt>Claim type</dt>
                <dd>{selectedBlock?.blockType}</dd>
              </div>
              <div>
                <dt>Category</dt>
                <dd>{selectedClassification.diligenceCategory}</dd>
              </div>
              <div>
                <dt>Risk level</dt>
                <dd class={`risk-copy ${riskLevelFrom(selectedClassification)}`}>{riskLevelFrom(selectedClassification)}</dd>
              </div>
              <div>
                <dt>Confidence</dt>
                <dd>{selectedClassification.confidence.toFixed(2)}</dd>
              </div>
            </dl>
          {:else}
            <p class="muted">Classification appears here once a block is selected.</p>
          {/if}
        </div>
      </div>

      <div class="insight-group">
        <div class="section-head">
          <strong>Your instruction</strong>
          <button type="button" class="ghost-link" onclick={() => (instruction = '')}>Clear</button>
        </div>
        <div class="card">
          <textarea
            bind:value={instruction}
            rows="4"
            placeholder="Make this more precise and suitable for an Investment Committee."
            disabled={!selectedBlock}
            maxlength="500"
          ></textarea>
          <div class="char-row">{instruction.length}/500</div>
        </div>
      </div>

      <div class="insight-group">
        <div class="section-head">
          <strong>AI Suggestion</strong>
          <span class="muted">{displaySuggestion(selectedSuggestion)?.generated ?? 'Awaiting generation'}</span>
        </div>
        <div class="card suggestion-card">
          {#if displaySuggestion(selectedSuggestion)}
            <p class="suggestion-text">{displaySuggestion(selectedSuggestion)?.text}</p>
            <div class="reasoning">
              <strong>Reasoning</strong>
              <p>{displaySuggestion(selectedSuggestion)?.reason}</p>
            </div>
          {:else}
            <p class="muted">No suggestion has been generated for this block yet. Select a block and use Smart Edit to create one.</p>
          {/if}
        </div>
      </div>

      {#if smartEditError}
        <p class="smart-edit-error">{smartEditError}</p>
      {/if}

      <div class="action-row">
        <button
          type="button"
          class="action ghost-action"
          disabled={!selectedSuggestion || smartEditStatus === 'saving'}
          onclick={() => decideSmartEditSuggestion('rejected')}
        >
          Reject
        </button>
        <button
          type="button"
          class="action ghost-action"
          disabled={!selectedBlock || smartEditStatus === 'generating'}
          onclick={generateSmartEditSuggestion}
        >
          {smartEditStatus === 'generating' ? 'Generating...' : 'Generate'}
        </button>
        <button
          type="button"
          class="action primary-action"
          disabled={!selectedSuggestion || smartEditStatus === 'saving'}
          onclick={() => decideSmartEditSuggestion('accepted')}
        >
          {smartEditStatus === 'saving' ? 'Saving...' : 'Accept'}
        </button>
      </div>

      <p class="apply-note">Accepting will update the block text and create a revision.</p>
    </aside>
    </div>
  </section>
</AppShell>

<style>
  .saved-pill {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 0.8rem 1rem;
    border: 1px solid rgba(34, 197, 94, 0.28);
    background: rgba(34, 197, 94, 0.1);
    color: var(--success);
    white-space: nowrap;
  }

  .smart-edit-shell {
    display: grid;
    grid-template-columns: 260px minmax(0, 1fr) 320px;
    gap: 1rem;
    min-height: 100%;
  }

  .slide-rail,
  .workspace-panel,
  .insight-panel {
    padding: 1rem;
    align-content: start;
  }

  .slide-rail {
    display: grid;
    gap: 1rem;
  }

  .rail-top h2,
  .workspace-head h2 {
    margin: 0.35rem 0 0;
  }

  .search-row {
    display: grid;
    grid-template-columns: 1fr 44px;
    gap: 0.75rem;
  }

  .search-row input,
  textarea {
    border-radius: 14px;
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.03);
    color: var(--ink);
    padding: 0.9rem 1rem;
  }

  .icon-filter,
  .dots {
    border-radius: 14px;
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.02);
    color: var(--ink-soft);
  }

  .slide-stack {
    display: grid;
    gap: 0.75rem;
  }

  .slide-item {
    display: grid;
    grid-template-columns: 88px 1fr;
    gap: 0.85rem;
    padding: 0.7rem;
    border-radius: 18px;
    border: 1px solid transparent;
  }

  .slide-item.selected {
    border-color: var(--line-strong);
    background: rgba(124, 58, 237, 0.1);
  }

  .slide-thumb {
    min-height: 58px;
    border-radius: 14px;
    border: 1px solid var(--line);
    padding: 0.65rem;
    display: grid;
    align-content: start;
    gap: 0.45rem;
  }

  .tone-default { background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)); }
  .tone-cover { background: linear-gradient(180deg, rgba(24,200,255,0.12), rgba(255,255,255,0.02)); }
  .tone-problem { background: linear-gradient(180deg, rgba(239,68,68,0.12), rgba(255,255,255,0.02)); }
  .tone-market { background: linear-gradient(180deg, rgba(124,58,237,0.14), rgba(255,255,255,0.02)); }
  .tone-solution { background: linear-gradient(180deg, rgba(34,197,94,0.12), rgba(255,255,255,0.02)); }
  .tone-product { background: linear-gradient(180deg, rgba(14,165,233,0.12), rgba(255,255,255,0.02)); }
  .tone-traction { background: linear-gradient(180deg, rgba(245,158,11,0.12), rgba(255,255,255,0.02)); }
  .tone-model { background: linear-gradient(180deg, rgba(148,163,184,0.15), rgba(255,255,255,0.02)); }
  .tone-team { background: linear-gradient(180deg, rgba(236,72,153,0.12), rgba(255,255,255,0.02)); }

  .mini-line,
  .mini-dot {
    border-radius: 999px;
    background: rgba(255,255,255,0.45);
  }

  .mini-line {
    height: 6px;
    width: 70%;
  }

  .mini-line.wide {
    width: 88%;
  }

  .mini-dot {
    width: 12px;
    height: 12px;
  }

  .slide-meta {
    display: flex;
    gap: 0.5rem;
    align-items: baseline;
  }

  .slide-copy small,
  .breadcrumbs,
  .char-row,
  .footer-row,
  .confidence {
    color: var(--muted);
  }

  .add-slide {
    min-height: 52px;
    border-radius: 16px;
    border: 1px solid var(--line);
    background: transparent;
    color: var(--ink-strong);
  }

  .workspace-panel {
    display: grid;
    gap: 1rem;
  }

  .breadcrumbs {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    font-size: 0.92rem;
  }

  .workspace-head {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
  }

  .context-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    margin-top: 0.9rem;
  }

  .context-chip,
  .role-pill,
  .chip {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 0.38rem 0.72rem;
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.03);
    font-size: 0.84rem;
  }

  .role-pill {
    text-transform: capitalize;
    color: var(--accent);
  }

  .tab-row {
    display: flex;
    gap: 1.2rem;
    align-items: end;
    padding-bottom: 0.2rem;
    border-bottom: 1px solid var(--line);
  }

  .tab {
    padding: 0.45rem 0;
  }

  .tab.active {
    border-bottom: 2px solid var(--accent);
    color: var(--ink-strong);
  }

  .tab strong {
    margin-left: 0.4rem;
  }

  .block-stack {
    display: grid;
    gap: 0.85rem;
  }

  .block-card {
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 1rem;
    background: rgba(255,255,255,0.03);
    display: grid;
    gap: 0.95rem;
  }

  .block-card.selected {
    border-color: var(--line-strong);
    box-shadow: inset 0 0 0 1px rgba(24, 200, 255, 0.12);
  }

  .block-top {
    display: grid;
    grid-template-columns: 40px 1fr 36px;
    gap: 0.8rem;
    align-items: start;
  }

  .block-index {
    width: 32px;
    height: 32px;
    border-radius: 10px;
    border: 1px solid var(--line);
    display: grid;
    place-items: center;
    color: var(--ink-soft);
    font-weight: 700;
  }

  .block-top p,
  .reasoning p,
  .card p {
    margin: 0.45rem 0 0;
    line-height: 1.5;
  }

  .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    align-items: center;
  }

  .chip {
    font-size: 0.8rem;
  }

  .footer-row,
  .risk-scale {
    display: flex;
    justify-content: space-between;
    gap: 0.9rem;
    flex-wrap: wrap;
  }

  .risk {
    position: relative;
    padding-left: 0.9rem;
  }

  .risk::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0.4rem;
    width: 0.42rem;
    height: 0.42rem;
    border-radius: 50%;
  }

  .risk.high::before { background: #ef4444; }
  .risk.medium::before { background: #f59e0b; }
  .risk.low::before { background: #22c55e; }
  .risk.info::before { background: #38bdf8; }

  .insight-panel {
    display: grid;
    gap: 1rem;
  }

  .insight-group {
    display: grid;
    gap: 0.7rem;
  }

  .section-head {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
  }

  .section-head a,
  .ghost-link {
    color: var(--accent);
    background: transparent;
    border: 0;
    padding: 0;
  }

  .card {
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 1rem;
    background: rgba(255,255,255,0.02);
  }

  .block-label {
    color: var(--muted);
    margin: 0;
  }

  .classification-card dl {
    margin: 0;
    display: grid;
    gap: 0.8rem;
  }

  .classification-card dt {
    color: var(--muted);
    font-size: 0.82rem;
  }

  .classification-card dd {
    margin: 0.28rem 0 0;
    font-weight: 600;
  }

  .risk-copy {
    text-transform: capitalize;
  }

  .risk-copy.high { color: #ef4444; }
  .risk-copy.medium { color: #f59e0b; }
  .risk-copy.low { color: #22c55e; }
  .risk-copy.informational { color: #38bdf8; }

  .char-row,
  .apply-note {
    font-size: 0.84rem;
  }

  .char-row {
    text-align: right;
    margin-top: 0.5rem;
  }

  .smart-edit-error {
    margin: 0;
    color: var(--danger);
    font-size: 0.86rem;
  }

  .field-list {
    display: grid;
    gap: 0.6rem;
  }

  .field-chip {
    display: grid;
    gap: 0.15rem;
    text-align: left;
    padding: 0.75rem 0.9rem;
    border-radius: 14px;
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.03);
    color: var(--ink);
  }

  .field-chip.active {
    border-color: var(--line-strong);
    background: rgba(24, 200, 255, 0.08);
  }

  .field-chip small,
  .selected-field small {
    color: var(--muted);
  }

  .selected-field {
    margin-top: 0.8rem;
    padding-top: 0.8rem;
    border-top: 1px solid var(--line);
    display: grid;
    gap: 0.35rem;
  }

  .suggestion-card {
    border-color: rgba(124, 58, 237, 0.24);
    background: linear-gradient(180deg, rgba(124, 58, 237, 0.08), rgba(255,255,255,0.03));
  }

  .suggestion-text {
    font-size: 1.05rem;
    line-height: 1.55;
  }

  .reasoning {
    margin-top: 1rem;
  }

  .action-row {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
  }

  .action {
    min-height: 50px;
    border-radius: 16px;
    font-weight: 600;
  }

  .ghost-action {
    border: 1px solid var(--line);
    background: transparent;
    color: var(--ink-strong);
  }

  .primary-action {
    border: 0;
    background: var(--gradient-brand);
    color: white;
    box-shadow: var(--shadow-glow-blue);
  }

  @media (max-width: 1320px) {
    .smart-edit-shell {
      grid-template-columns: 240px minmax(0, 1fr) 320px;
    }
  }

  @media (max-width: 1100px) {
    .smart-edit-shell {
      grid-template-columns: 1fr;
      min-height: auto;
    }
  }

  @media (max-width: 720px) {
    .block-top {
      grid-template-columns: 32px 1fr;
    }

    .dots {
      display: none;
    }

    .action-row {
      grid-template-columns: 1fr;
    }
  }
</style>
