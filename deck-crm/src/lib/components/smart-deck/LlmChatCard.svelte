<script lang="ts">
  import type { SmartDeckChatMessage, SmartDeckGenerationStatus, SmartDeckSourceSlide } from '$lib/api/smartDeckWorkspace';
  import { detectSmartDeckSubject } from '$lib/utils/detectSmartDeckSubject';
  import { smartDeckSubjectActionById, smartDeckSubjectPromptActions } from '$lib/data/smartDeckSubjectPrompts';
  import { smartDeckSubjectRegistry, getSmartDeckDeckType } from '$lib/data/smartDeckSubjectRegistry';
  import type {
    SmartDeckDeckType,
    SmartDeckGenerationTopicRequest,
    SmartDeckSubject,
  } from '$lib/types/smart-deck-subjects';
  import InfoBubble from './InfoBubble.svelte';

  type SlideAgentUiState = 'idle' | 'thinking' | 'rendering' | 'saving' | 'completed' | 'failed';

  interface Props {
    chatMessages?: SmartDeckChatMessage[];
    selectedSourceSlideIds?: string[];
    selectedSlides?: SmartDeckSourceSlide[];
    deckAudience?: string | null;
    deckPurpose?: string | null;
    preferredAudience?: string | null;
    preferredDeckType?: SmartDeckDeckType | null;
    preferredModel?: string | null;
    preferredSelectedSubject?: SmartDeckSubject | null;
    preferredSelectedActionId?: string | null;
    selectedElementId?: string | null;
    generationStatus?: SmartDeckGenerationStatus;
    activeBatchId?: string | null;
    previewMode?: boolean;
    agentRunState?: SlideAgentUiState;
    generatedVersionCount?: number;
    onSendMessage?: (request: SmartDeckGenerationTopicRequest) => void | Promise<void>;
    onContextChange?: (context: {
      audience: string | null;
      deckType: SmartDeckDeckType;
      preferredModel: string | null;
      selectedSubject: SmartDeckSubject;
      selectedActionId: string | null;
    }) => void | Promise<void>;
    onReviewChanges?: () => void;
    onApplyAll?: () => void | Promise<void>;
  }

  let {
    chatMessages = [],
    selectedSourceSlideIds = [],
    selectedSlides = [],
    deckAudience = null,
    deckPurpose = null,
    preferredAudience = null,
    preferredDeckType = null,
    preferredModel = null,
    preferredSelectedSubject = null,
    preferredSelectedActionId = null,
    selectedElementId = null,
    generationStatus = 'idle',
    activeBatchId = null,
    previewMode = false,
    agentRunState = 'idle',
    generatedVersionCount = 0,
    onSendMessage,
    onContextChange,
    onReviewChanges,
    onApplyAll
  }: Props = $props();

  let prompt = $state('');
  let audience = $state('VC investor');
  let deckType = $state<SmartDeckDeckType>('unknown');
  let model = $state('gpt-5');
  let selectedSubject = $state<SmartDeckSubject>('unknown');
  let selectedActionId = $state<string>('');
  let visualRunState = $state<SlideAgentUiState>('idle');
  let lastPersistedContextSignature = $state('');
  let hydratedContext = $state(false);
  let modelSettingsOpen = $state(false);

  const detectedSubjects = $derived(
    selectedSlides.map((slide) =>
      detectSmartDeckSubject(
        slide.title,
        slide.extractedText,
        slide.blocks?.map((block) => String((block as { type?: unknown }).type ?? '')).filter(Boolean),
        slide.title,
        deckPurpose ?? deckAudience
      )
    )
  );
  const detectedSubject = $derived(detectedSubjects[0]?.subject ?? 'unknown');
  const selectedSubjectDefinition = $derived(smartDeckSubjectRegistry.find((item) => item.id === selectedSubject) ?? null);
  const subjectActions = $derived(
    smartDeckSubjectPromptActions.filter((action) => {
      const subjectMatches = selectedSubject === 'unknown' || action.subject === selectedSubject;
      const deckMatches = action.deckTypes.includes(deckType) || deckType === 'unknown';
      return subjectMatches && deckMatches;
    })
  );
  const activeAction = $derived(smartDeckSubjectActionById[selectedActionId] ?? subjectActions[0] ?? null);

  const audienceOptions = [
    'VC investor',
    'Angel',
    'Strategic',
    'LP',
    'Internal review',
    'Sample day'
  ];

  const deckTypeOptions: Array<{ label: string; value: SmartDeckDeckType }> = [
    { label: 'Unknown', value: 'unknown' },
    { label: 'Startup pitch', value: 'startup_pitch' },
    { label: 'VC fund pitch', value: 'vc_fund_pitch' }
  ];

  $effect(() => {
    if (selectedSlides.length === 0) return;
    if (selectedSubject === 'unknown' && detectedSubject !== 'unknown') {
      selectedSubject = detectedSubject;
    }
  });

  $effect(() => {
    const availableActionIds = new Set(subjectActions.map((action) => action.id));
    const firstAction = subjectActions[0];
    if (selectedActionId && !availableActionIds.has(selectedActionId) && firstAction) {
      selectedActionId = firstAction.id;
      prompt = firstAction.prompt;
      return;
    }
    if (!selectedActionId && firstAction) {
      selectedActionId = firstAction.id;
      prompt = firstAction.prompt;
    }
  });

  $effect(() => {
    deckType = preferredDeckType ?? getSmartDeckDeckType(deckAudience, deckPurpose);
  });

  $effect(() => {
    if (hydratedContext) return;
    audience = preferredAudience ?? deckAudience ?? 'VC investor';
    deckType = preferredDeckType ?? getSmartDeckDeckType(deckAudience, deckPurpose);
    model = preferredModel ?? 'gpt-5';
    selectedSubject = preferredSelectedSubject ?? 'unknown';
    selectedActionId = preferredSelectedActionId ?? '';
    hydratedContext = true;
  });

  $effect(() => {
    const contextSignature = `${audience ?? ''}|${deckType}|${model}|${selectedSubject}|${selectedActionId ?? ''}`;
    if (!lastPersistedContextSignature) {
      lastPersistedContextSignature = contextSignature;
      return;
    }
    if (contextSignature === lastPersistedContextSignature) return;
    lastPersistedContextSignature = contextSignature;
    void onContextChange?.({
      audience: audience || null,
      deckType,
      preferredModel: model || null,
      selectedSubject,
      selectedActionId: selectedActionId || null
    });
  });

  const modelOptions = [
    { label: 'OpenAI · GPT-5', value: 'gpt-5' },
    { label: 'OpenAI · GPT-4.1', value: 'gpt-4.1' },
    { label: 'OpenRouter · GPT-4o', value: 'openai/gpt-4o' },
    { label: 'OpenRouter · GPT-4.1 Mini', value: 'openai/gpt-4.1-mini' },
    { label: 'OpenRouter · Claude Sonnet 4.5', value: 'anthropic/claude-sonnet-4.5' },
    { label: 'Claude · Sonnet 4.5', value: 'claude-sonnet-4-5' },
    { label: 'Claude · Opus 4.1', value: 'claude-opus-4-1' }
  ];

  const selectedProviderLabel = $derived(model.includes('/') ? 'OpenRouter' : model.startsWith('claude') ? 'Claude' : 'OpenAI');

  const uiCopy = $derived<Record<SlideAgentUiState, { title: string; subtitle: string }>>({
    idle: {
      title: `${selectedProviderLabel} ready`,
      subtitle: 'Select a subject so the LLM can apply the right investor logic.'
    },
    thinking: {
      title: `${selectedProviderLabel} is working...`,
      subtitle: 'Reading selected slides and building the redesign.'
    },
    rendering: {
      title: `${selectedProviderLabel} is rendering...`,
      subtitle: 'Creating editable design versions.'
    },
    saving: {
      title: `Saving ${selectedProviderLabel} output...`,
      subtitle: 'Adding them to your workspace.'
    },
    completed: {
      title: 'New versions ready',
      subtitle: 'Review the generated slide changes.'
    },
    failed: {
      title: 'Something went wrong',
      subtitle: 'The agent could not complete this request.'
    }
  });
  const isAgentRunning = $derived(
    agentRunState === 'thinking' || agentRunState === 'rendering' || agentRunState === 'saving' || generationStatus === 'running'
  );
  const canSubmitPrompt = $derived(!previewMode && !isAgentRunning && prompt.trim().length > 0 && selectedSourceSlideIds.length > 0);
  const isAgentCompleted = $derived(agentRunState === 'completed');
  const isAgentFailed = $derived(agentRunState === 'failed');
  const selectedCountLabel = $derived(
    selectedSourceSlideIds.length === 1 ? '1 selected slide' : `${selectedSourceSlideIds.length} selected slides`
  );
  const selectedSlideNoun = $derived(selectedSourceSlideIds.length === 1 ? 'slide' : 'slides');
  const selectedSlideLabel = $derived(selectedSlides.length > 0 ? selectedCountLabel : 'No slides selected');

  $effect(() => {
    if (!isAgentRunning) {
      visualRunState = agentRunState;
      return;
    }

    visualRunState = agentRunState === 'idle' ? 'thinking' : agentRunState;
    const interval = window.setInterval(() => {
      visualRunState = visualRunState === 'thinking' ? 'rendering' : visualRunState === 'rendering' ? 'saving' : 'saving';
    }, 1350);

    return () => window.clearInterval(interval);
  });

  async function submitPrompt() {
    const nextPrompt = prompt.trim();
    if (!nextPrompt || previewMode || isAgentRunning) return;

    prompt = '';
    await onSendMessage?.({
      prompt: nextPrompt,
      selectedSourceSlideIds,
      activeSourceSlideId: selectedSourceSlideIds[0] ?? null,
      selectedElementId,
      deckType,
      audience,
      preferredModel: model,
      selectedSubject,
      detectedSubjects,
      actionId: activeAction?.id ?? null,
      actionPrompt: activeAction?.prompt ?? null,
      userPrompt: nextPrompt,
      latestBatchId: activeBatchId
    });
  }

  const showResultState = $derived(isAgentCompleted || isAgentFailed);
</script>

<article class="panel llm-chat-card">
  <header class="card-header">
    <div>
      <h2>{uiCopy[visualRunState].title}</h2>
      <p>{uiCopy[visualRunState].subtitle}</p>
    </div>
    <div class="card-header__tools">
      <InfoBubble
        label="Slide generation help"
        text="Select source slides, then send a prompt. If a design element is selected, the prompt refines that element instead of generating a full slide."
      />
      <button
        class="model-gear"
        type="button"
        aria-label="Model settings"
        aria-expanded={modelSettingsOpen}
        onclick={() => (modelSettingsOpen = !modelSettingsOpen)}
      >
        <span aria-hidden="true">⛭</span>
      </button>
      {#if modelSettingsOpen}
        <div class="model-popover" role="dialog" aria-label="Model settings">
          <label>
            <span>Model</span>
            <select bind:value={model} disabled={previewMode || isAgentRunning}>
              {#each modelOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>
          <small>Saved for this deck and used for the next generation run.</small>
        </div>
      {/if}
      {#if activeBatchId}
        <span class="pill">Iteration ready</span>
      {/if}
    </div>
  </header>

  {#if isAgentRunning}
    <section class="agent-loader-card" aria-live="polite">
      <div class="agent-orb" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
      </div>

      <h3>{uiCopy[visualRunState].title}</h3>
      <p>{uiCopy[visualRunState].subtitle}</p>

      <div class="agent-mini-context">
        Working on {selectedSourceSlideIds.length} selected {selectedSlideNoun}
      </div>
    </section>
  {:else if showResultState}
    <section class={`agent-result-card ${agentRunState}`} aria-live="polite">
      <div>
        <h3>{uiCopy[agentRunState].title}</h3>
        <p>{uiCopy[agentRunState].subtitle}</p>
        {#if isAgentCompleted}
          <span class="agent-mini-context">
            {generatedVersionCount || selectedSourceSlideIds.length} version{(generatedVersionCount || selectedSourceSlideIds.length) === 1 ? '' : 's'} created
          </span>
        {/if}
      </div>

      {#if isAgentCompleted}
        <div class="agent-window__actions">
          <button class="button secondary" type="button" onclick={() => onReviewChanges?.()}>Review changes</button>
          <button class="button" type="button" onclick={() => onApplyAll?.()}>Apply all</button>
        </div>
      {/if}
    </section>
  {:else}
    <div class="assistant-ready">
      <strong>{selectedSlideLabel}</strong>
      <span>{uiCopy.idle.subtitle}</span>
      {#if selectedElementId}
        <span class="pill">Element selected</span>
      {/if}
    </div>

    {#if previewMode}
      <div class="preview-lock-note" role="status">
        <strong>Preview is active</strong>
        <span>Apply or discard it before generating another change.</span>
      </div>
    {/if}

    <div class="subject-grid">
      <label class="deck-ai-panel__field">
        <span>Deck type</span>
        <select bind:value={deckType} disabled={previewMode || isAgentRunning}>
          {#each deckTypeOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>

      <label class="deck-ai-panel__field">
        <span>Audience</span>
        <select bind:value={audience} disabled={previewMode || isAgentRunning}>
          {#each audienceOptions as option}
            <option value={option}>{option}</option>
          {/each}
        </select>
      </label>

      <label class="deck-ai-panel__field">
        <span>Topic</span>
        <select bind:value={selectedSubject} disabled={previewMode || isAgentRunning}>
          <option value="unknown">Auto-detected: {detectedSubject === 'unknown' ? 'Unknown' : detectedSubject}</option>
          {#each smartDeckSubjectRegistry as subject}
            <option value={subject.id}>{subject.label}</option>
          {/each}
        </select>
      </label>
    </div>

    <div class="deck-ai-panel__pill-row">
      <span class="pill">Detected topic: {detectedSubject === 'unknown' ? 'Unknown' : smartDeckSubjectRegistry.find((subject) => subject.id === detectedSubject)?.label ?? detectedSubject}</span>
      <span class="pill">Audience: {audience}</span>
      <span class="pill">Prompt: {activeAction?.label ?? 'Custom instruction'}</span>
    </div>

    {#if selectedSubjectDefinition}
      <p class="topic-caption">{selectedSubjectDefinition.description}</p>
    {/if}

    <div class="deck-ai-panel__stack">
      {#each subjectActions as action}
        <button
          type="button"
          class={`action-card ${selectedActionId === action.id ? 'active' : ''}`}
          disabled={previewMode || isAgentRunning}
          onclick={() => {
            selectedActionId = action.id;
            selectedSubject = action.subject;
            prompt = action.prompt;
          }}
        >
          <strong>{action.label}</strong>
          <span>{action.description}</span>
        </button>
      {/each}
    </div>

    <div class="chat-log">
      {#if chatMessages.length === 0}
      <div class="chat-empty">
        <div class="chat-empty__head">
          <strong>{selectedSourceSlideIds.length > 0 ? `${selectedProviderLabel} is ready to redesign ${selectedCountLabel}` : 'Select one or more slides'}</strong>
          <InfoBubble
            label="Generation request help"
            text="Your selected source slide IDs are sent to Deck AIStack. The service loads slide data, brand rules, the detected topic, and saved workspace context before creating editable versions."
            side="right"
          />
          </div>
        </div>
      {:else}
        {#each chatMessages as message}
          <div class={`chat-message ${message.role}`}>
            {#if message.role !== 'assistant'}
              <span>{message.role}</span>
            {/if}
            <p>{message.content}</p>
            {#if message.selectedSourceSlideIds?.length}
              <small>{message.selectedSourceSlideIds.length} source slide{message.selectedSourceSlideIds.length === 1 ? '' : 's'} used</small>
            {/if}
          </div>
        {/each}
      {/if}
    </div>

    <form class="chat-form" onsubmit={(event) => { event.preventDefault(); void submitPrompt(); }}>
    <textarea
      bind:value={prompt}
      placeholder={activeAction?.prompt ?? 'Ask the LLM to redesign, regenerate, or refine these slides...'}
      rows="4"
      disabled={previewMode || isAgentRunning}
    ></textarea>
      <button class="button" type="submit" disabled={!canSubmitPrompt}>
        {previewMode ? 'Preview locked' : isAgentRunning ? 'Rendering...' : selectedElementId ? 'Refine selected element' : 'Redesign selected slides'}
      </button>
    </form>
  {/if}
</article>

<style>
  .llm-chat-card {
    min-height: 0;
    height: 100%;
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr) auto;
    gap: 1rem;
    padding: 1rem;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
    flex-wrap: wrap;
  }

  .card-header p {
    margin: 0.2rem 0 0;
    color: var(--muted);
    font-size: 0.86rem;
  }

  .card-header__tools,
  .assistant-ready,
  .chat-empty__head {
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }

  h2 {
    margin: 0;
  }

  .assistant-ready {
    justify-content: space-between;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.6rem 0.7rem;
    background: var(--surface-soft);
  }

  .preview-lock-note {
    display: grid;
    gap: 0.25rem;
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    background: var(--surface-active);
    padding: 0.7rem 0.8rem;
  }

  .preview-lock-note span {
    color: var(--muted);
    font-size: 0.84rem;
    line-height: 1.35;
  }

  .card-header__tools {
    position: relative;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .model-gear {
    width: 34px;
    height: 34px;
    display: inline-grid;
    place-items: center;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-soft);
    color: var(--ink);
  }

  .model-popover {
    position: absolute;
    top: calc(100% + 0.5rem);
    right: 0;
    z-index: 3;
    min-width: 14rem;
    padding: 0.7rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface);
    box-shadow: var(--shadow);
    display: grid;
    gap: 0.55rem;
  }

  .model-popover label {
    display: grid;
    gap: 0.35rem;
  }

  .model-popover select {
    width: 100%;
  }

  .model-popover small {
    color: var(--muted);
    line-height: 1.35;
  }

  .subject-grid {
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .action-card {
    display: grid;
    gap: 0.3rem;
    text-align: left;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-soft);
    color: var(--ink);
    padding: 0.75rem 0.85rem;
    cursor: pointer;
  }

  .action-card.active,
  .action-card:hover,
  .action-card:focus-visible {
    border-color: var(--line-strong);
    background: var(--surface-active);
  }

  .action-card strong {
    font-size: 0.88rem;
  }

  .action-card span {
    color: var(--muted);
    font-size: 0.78rem;
    line-height: 1.35;
  }

  .chat-log {
    min-height: 12rem;
    overflow-y: auto;
    display: grid;
    align-content: start;
    gap: 0.75rem;
  }

  .agent-loader-card,
  .agent-result-card {
    min-height: 25rem;
    display: grid;
    align-content: center;
    justify-items: center;
    gap: 1rem;
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    padding: 1.25rem;
    background: var(--surface-strong);
    box-shadow: var(--shadow);
    text-align: center;
  }

  .agent-result-card.failed {
    border-color: var(--danger);
    background: var(--surface-strong);
  }

  .agent-orb {
    width: 78px;
    height: 78px;
    border-radius: 999px;
    position: relative;
    background: var(--gradient-brand);
    filter: drop-shadow(var(--shadow-glow-blue));
    animation: orbPulse 1.8s ease-in-out infinite;
  }

  .agent-orb::before {
    content: '';
    position: absolute;
    inset: -7px;
    border-radius: inherit;
    border: 1px solid var(--line-strong);
    animation: orbRing 1.8s ease-in-out infinite;
  }

  .agent-orb span {
    position: absolute;
    width: 9px;
    height: 9px;
    border-radius: 999px;
    background: var(--button-primary-ink);
    box-shadow: var(--shadow-glow-blue);
  }

  .agent-orb span:nth-child(1) {
    top: 18px;
    left: 22px;
    animation: dotFloat 1.4s ease-in-out infinite;
  }

  .agent-orb span:nth-child(2) {
    top: 32px;
    right: 18px;
    animation: dotFloat 1.4s ease-in-out 0.2s infinite;
  }

  .agent-orb span:nth-child(3) {
    bottom: 18px;
    left: 34px;
    animation: dotFloat 1.4s ease-in-out 0.4s infinite;
  }

  .agent-loader-card h3,
  .agent-result-card h3 {
    margin: 0;
    font-size: 1rem;
    color: var(--ink-strong);
  }

  .agent-loader-card p,
  .agent-result-card p {
    margin: 0.35rem 0 0;
    color: var(--muted);
    font-size: 0.86rem;
  }

  .agent-mini-context {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.45rem 0.75rem;
    border-radius: 999px;
    background: var(--surface-chip);
    border: 1px solid var(--line-strong);
    color: var(--accent);
    font-size: 0.78rem;
  }

  .agent-window__actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .chat-empty {
    min-height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    place-items: center;
    text-align: center;
    padding: 1rem;
    border: 1px dashed var(--line);
    border-radius: 8px;
  }

  .chat-message {
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.75rem;
    display: grid;
    gap: 0.35rem;
    background: var(--surface-soft);
  }

  .chat-message.user {
    border-color: var(--line-strong);
  }

  .chat-message span,
  .chat-message small,
  .muted {
    color: var(--muted);
  }

  .chat-message p {
    margin: 0;
  }

  .chat-form {
    display: grid;
    gap: 0.75rem;
  }

  textarea {
    width: 100%;
    resize: vertical;
    min-height: 6rem;
    border-radius: 8px;
    border: 1px solid var(--line);
    background: var(--surface-input);
    color: inherit;
    padding: 0.8rem;
    font: inherit;
  }

  textarea::placeholder {
    color: var(--muted);
    font-size: 0.82rem;
  }

  .button {
    justify-content: center;
  }

  @keyframes orbPulse {
    0%,
    100% {
      transform: scale(0.96);
      opacity: 0.82;
    }

    50% {
      transform: scale(1.04);
      opacity: 1;
    }
  }

  @keyframes orbRing {
    0% {
      transform: scale(0.92);
      opacity: 0.75;
    }

    100% {
      transform: scale(1.18);
      opacity: 0;
    }
  }

  @keyframes dotFloat {
    0%,
    100% {
      transform: translateY(0);
      opacity: 0.65;
    }

    50% {
      transform: translateY(-6px);
      opacity: 1;
    }
  }
</style>
