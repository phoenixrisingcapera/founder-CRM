<script lang="ts">
  import type { DesignBatchPreview, GeneratedSlideVersion } from '@deck-aistack-codes/shared';
  import DesignVersionPanel from '$components/deck-shell/DesignVersionPanel.svelte';
  import type { AdaptationSuggestion, AnalysisFinding } from '$types/domain';

  interface PreparedIteration {
    scopeLabel: string;
    prompt: string;
    selectedSlides: string[];
    actionCount: number;
  }

  interface Props {
    latestBatch?: DesignBatchPreview | null;
    generationStatus?: string;
    scope: 'selected_slides' | 'whole_deck';
    instruction: string;
    selectedFindings: AnalysisFinding[];
    selectedSuggestions: AdaptationSuggestion[];
    selectedVersions?: GeneratedSlideVersion[];
    canPrepareIteration: boolean;
    preparedIteration?: PreparedIteration | null;
    isCreatingIteration?: boolean;
    generationMessage?: string | null;
    shellError?: string | null;
    onScopeChange?: (scope: 'selected_slides' | 'whole_deck') => void;
    onInstructionChange?: (instruction: string) => void;
    onPrepareIteration?: () => void;
    onCreateIteration?: () => void;
    onAcceptGeneratedVersion?: (versionId: string, sourceSlideId: string | null) => void;
    onRejectGeneratedVersion?: (versionId: string, sourceSlideId: string | null) => void;
    onOpenSmartEdit?: () => void;
    onOpenBatches?: () => void;
    onOpenChanges?: () => void;
  }

  let {
    latestBatch = null,
    generationStatus = 'idle',
    scope,
    instruction,
    selectedFindings,
    selectedSuggestions,
    selectedVersions = [],
    canPrepareIteration,
    preparedIteration = null,
    isCreatingIteration = false,
    generationMessage = null,
    shellError = null,
    onScopeChange,
    onInstructionChange,
    onPrepareIteration,
    onCreateIteration,
    onAcceptGeneratedVersion,
    onRejectGeneratedVersion,
    onOpenSmartEdit,
    onOpenBatches,
    onOpenChanges
  }: Props = $props();

  const quickActions = [
    'Make this more investor-ready.',
    'Simplify the message hierarchy.',
    'Tighten the visual narrative.',
    'Make this suitable for a VC meeting.'
  ];
</script>

<aside class="deck-ai-panel panel">
  <section class="deck-ai-panel__group">
      <div class="section-head">
        <strong>AI design studio</strong>
        <span class="muted">{selectedVersions.length > 0 ? `${selectedVersions.length} generated versions` : latestBatch ? `Latest version ${latestBatch.batchNumber}` : 'No versions yet'}</span>
      </div>
      <p class="muted">Generation status: {generationStatus}</p>

    <label class="deck-ai-panel__field">
      <span>Scope</span>
      <select
        bind:value={scope}
        onchange={(event) => {
          const target = event.currentTarget as HTMLSelectElement;
          onScopeChange?.(target.value as 'selected_slides' | 'whole_deck');
        }}
      >
        <option value="selected_slides">Selected slides</option>
        <option value="whole_deck">Whole deck</option>
      </select>
    </label>

    <label class="deck-ai-panel__field">
      <span>Iteration brief</span>
      <textarea
        bind:value={instruction}
        rows="5"
        placeholder="Tell Deck AIStack what should change in this next design iteration."
        oninput={(event) => {
          const target = event.currentTarget as HTMLTextAreaElement;
          onInstructionChange?.(target.value);
        }}
      ></textarea>
    </label>

    <div class="deck-ai-panel__pill-row">
      <span class="pill">Use uploaded deck</span>
      <span class="pill">Use slide structure</span>
      <span class="pill">Use audience context</span>
    </div>

    <div class="deck-ai-panel__quick-actions">
      {#each quickActions as action}
        <button
          type="button"
          class="pill"
          onclick={() => {
            onInstructionChange?.(action);
          }}
        >
          {action.replace('.', '')}
        </button>
      {/each}
    </div>

    <div class="deck-ai-panel__button-row">
      <button type="button" class="button" onclick={() => onPrepareIteration?.()} disabled={!canPrepareIteration}>
        Prepare iteration
      </button>
      <button type="button" class="button secondary" onclick={() => onOpenSmartEdit?.()}>
        Open Smart Edit
      </button>
    </div>

    {#if shellError}
      <p class="deck-ai-panel__error">{shellError}</p>
    {/if}

    {#if generationMessage}
      <p class="muted">{generationMessage}</p>
    {/if}
  </section>

  {#if preparedIteration}
    <section class="deck-ai-panel__group deck-ai-panel__group--prepared">
      <div class="section-head">
        <strong>Prepared iteration</strong>
        <span class="pill">{preparedIteration.scopeLabel}</span>
      </div>
      <p class="muted">{preparedIteration.prompt}</p>
      <div class="deck-ai-panel__pill-row">
        {#each preparedIteration.selectedSlides as title}
          <span class="pill">{title}</span>
        {/each}
      </div>
      <p class="muted">This pass would use {preparedIteration.actionCount} findings and recommendations as context before a new design version is created.</p>
      <div class="deck-ai-panel__button-row">
        <button type="button" class="button" onclick={() => onCreateIteration?.()} disabled={isCreatingIteration}>
          {isCreatingIteration ? 'Creating version...' : 'Create design version'}
        </button>
        <button type="button" class="button secondary" onclick={() => onOpenBatches?.()}>Open versions</button>
        <button type="button" class="button secondary" onclick={() => onOpenChanges?.()}>Open diligence</button>
      </div>
    </section>
  {/if}

  <section class="deck-ai-panel__group">
    <DesignVersionPanel
      versions={selectedVersions}
      isSubmitting={isCreatingIteration}
      onAccept={onAcceptGeneratedVersion}
      onReject={onRejectGeneratedVersion}
    />
  </section>

  <section class="deck-ai-panel__group">
    <div class="section-head">
      <strong>Diligence findings</strong>
      <span class="muted">{selectedFindings.length} on this slide</span>
    </div>
    {#if selectedFindings.length > 0}
      <div class="deck-ai-panel__stack">
        {#each selectedFindings as finding}
          <article class="deck-ai-panel__note">
            <div class="section-head">
              <strong>{finding.title}</strong>
              <span class={`pill pill--${finding.severity}`}>{finding.severity}</span>
            </div>
            <p>{finding.detail}</p>
          </article>
        {/each}
      </div>
    {:else}
      <p class="muted">This slide has no diligence findings yet.</p>
    {/if}
  </section>

  <section class="deck-ai-panel__group">
    <div class="section-head">
      <strong>Audience recommendations</strong>
      <span class="muted">{selectedSuggestions.length}</span>
    </div>
    {#if selectedSuggestions.length > 0}
      <div class="deck-ai-panel__stack">
        {#each selectedSuggestions as suggestion}
          <article class="deck-ai-panel__note">
            <strong>{suggestion.title}</strong>
            <p>{suggestion.reason}</p>
          </article>
        {/each}
      </div>
    {:else}
      <p class="muted">Recommendations will appear here once adaptation suggestions exist for the selected slide.</p>
    {/if}
  </section>
</aside>

<style>
  .deck-ai-panel {
    display: grid;
    gap: 1rem;
    align-content: start;
    padding: 1rem;
  }

  .deck-ai-panel__group {
    display: grid;
    gap: 0.9rem;
    border: 1px solid var(--line);
    border-radius: 22px;
    background: var(--surface-soft);
    padding: 1rem;
  }

  .deck-ai-panel__group--prepared {
    border-color: var(--line-strong);
  }

  .deck-ai-panel__field {
    display: grid;
    gap: 0.45rem;
  }

  .deck-ai-panel__field span {
    font-size: 0.86rem;
    color: var(--muted);
  }

  .deck-ai-panel__field select,
  .deck-ai-panel__field textarea {
    width: 100%;
    border-radius: 16px;
    border: 1px solid var(--line);
    background: var(--surface-input);
    color: var(--ink);
    padding: 0.85rem 0.95rem;
  }

  .deck-ai-panel__pill-row,
  .deck-ai-panel__button-row,
  .deck-ai-panel__quick-actions {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
  }

  .deck-ai-panel__stack {
    display: grid;
    gap: 0.75rem;
  }

  .deck-ai-panel__note {
    border: 1px solid var(--line);
    border-radius: 22px;
    background: var(--surface-muted);
    padding: 1rem;
  }

  .deck-ai-panel__note p {
    margin: 0.55rem 0 0;
    line-height: 1.6;
  }

  .deck-ai-panel__error {
    margin: 0;
    color: var(--danger);
  }

  .pill--high {
    color: var(--danger);
  }

  .pill--medium {
    color: var(--warn);
  }

  .pill--low {
    color: var(--success);
  }
</style>
