<script lang="ts">
  import type { AiDesignCommand, AiDesignPreset, AiDesignScope } from '$lib/types/ai-design';

  interface Props {
    open: boolean;
    deckTitle?: string;
    slideCount?: number;
    contextLabel?: string | null;
    providerLabel?: string;
    currentSlideTitle?: string;
    selectedSlideCount: number;
    target: AiDesignScope;
    instruction: string;
    preset?: AiDesignPreset | null;
    isCreating?: boolean;
    onClose?: () => void;
    onTargetChange?: (target: AiDesignScope) => void;
    onInstructionChange?: (instruction: string) => void;
    onPresetChange?: (preset: AiDesignPreset | null) => void;
    onCreateVersion?: (command: AiDesignCommand) => void;
  }

  let {
    open,
    deckTitle = 'Current deck',
    slideCount = 0,
    contextLabel = null,
    providerLabel = 'Claude',
    currentSlideTitle,
    selectedSlideCount,
    target,
    instruction,
    preset = 'investor_ready',
    isCreating = false,
    onClose,
    onTargetChange,
    onInstructionChange,
    onPresetChange,
    onCreateVersion
  }: Props = $props();

  const quickPrompts = [
    { preset: 'investor_ready', label: 'Investor-ready', prompt: 'Make this more investor-ready.' },
    { preset: 'visual_hierarchy', label: 'Stronger visual hierarchy', prompt: 'Tighten the visual hierarchy.' },
    { preset: 'narrative_flow', label: 'Cleaner narrative', prompt: 'Clean up the narrative flow.' },
    { preset: 'sharper_vc_version', label: 'Sharper VC version', prompt: 'Create a sharper VC version.' }
  ];

  function scopeLabel() {
    if (target === 'current_slide') return 'Current slide';
    if (target === 'selected_slides') return `${selectedSlideCount} selected slide${selectedSlideCount === 1 ? '' : 's'}`;
    return slideCount > 0 ? `${slideCount} slides` : 'Whole deck';
  }

  function submitCommand() {
    const command = instruction.trim();
    if (!command) return;
    onCreateVersion?.({
      scope: target,
      command,
      preset
    });
  }
</script>

{#if open}
  <div class="deck-ai-chat-popup" role="dialog" aria-label="AI Design Assistant">
    <div class="deck-ai-chat-popup__head">
      <div>
        <div class="eyebrow">AI Design Assistant</div>
        <h3>Create a new design version</h3>
        <p>Use {providerLabel} to improve the selected deck content and generate a reviewable version.</p>
      </div>
      <button type="button" class="deck-ai-chat-popup__close" aria-label="Close assistant" onclick={() => onClose?.()}>
        ×
      </button>
    </div>

    <div class="deck-ai-chat-popup__context">
      <div>
        <span>Deck</span>
        <strong>{deckTitle}</strong>
      </div>
      <div>
        <span>Mode</span>
        <strong>{scopeLabel()}</strong>
      </div>
      {#if contextLabel}
        <div>
          <span>Context</span>
          <strong>{contextLabel}</strong>
        </div>
      {/if}
    </div>

    <div class="deck-ai-chat-popup__scope">
      <span class="muted">Scope</span>
      <div class="deck-ai-chat-popup__targets">
        <button
          type="button"
          class:active={target === 'current_slide'}
          onclick={() => onTargetChange?.('current_slide')}
        >
          Current slide
        </button>
        <button
          type="button"
          class:active={target === 'selected_slides'}
          onclick={() => onTargetChange?.('selected_slides')}
        >
          Selected slides
        </button>
        <button
          type="button"
          class:active={target === 'whole_deck'}
          onclick={() => onTargetChange?.('whole_deck')}
        >
          Whole deck
        </button>
      </div>
      {#if target === 'current_slide' && currentSlideTitle}
        <p class="muted">Current slide: {currentSlideTitle}</p>
      {/if}
    </div>

    <span class="muted">Suggested actions</span>
    <div class="deck-ai-chat-popup__quick-prompts">
      {#each quickPrompts as prompt}
        <button
          type="button"
          class="pill"
          class:active={preset === prompt.preset}
          onclick={() => {
            onPresetChange?.(prompt.preset as AiDesignPreset);
            onInstructionChange?.(prompt.prompt);
          }}
        >
          {prompt.label}
        </button>
      {/each}
    </div>

    <label class="deck-ai-chat-popup__field">
      <span>Instruction</span>
      <textarea
        rows="5"
        bind:value={instruction}
        placeholder="Describe the design direction, audience shift, or slide improvements you want."
        oninput={(event) => {
          const target = event.currentTarget as HTMLTextAreaElement;
          onInstructionChange?.(target.value);
        }}
      ></textarea>
    </label>

    <div class="deck-ai-chat-popup__actions">
      <button type="button" class="button" onclick={submitCommand} disabled={isCreating || !instruction.trim()}>
        {isCreating ? 'Creating version...' : 'Create design version'}
      </button>
      <button type="button" class="button secondary" onclick={() => onClose?.()}>Cancel</button>
    </div>
  </div>
{/if}

<style>
  .deck-ai-chat-popup {
    position: fixed;
    right: 1.25rem;
    bottom: 1.25rem;
    z-index: 65;
    width: min(420px, calc(100vw - 2rem));
    border: 1px solid var(--line-strong);
    border-radius: 26px;
    background:
      radial-gradient(circle at top right, color-mix(in srgb, var(--accent) 18%, transparent), transparent 42%),
      var(--surface);
    box-shadow: var(--shadow-glow-blue);
    padding: 1rem;
    display: grid;
    gap: 0.95rem;
  }

  .deck-ai-chat-popup__head,
  .deck-ai-chat-popup__actions {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
  }

  .deck-ai-chat-popup__head h3 {
    margin: 0.2rem 0 0;
  }

  .deck-ai-chat-popup__head p {
    margin: 0.35rem 0 0;
    color: var(--muted);
    line-height: 1.45;
  }

  .deck-ai-chat-popup__context {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.6rem;
  }

  .deck-ai-chat-popup__context div {
    border: 1px solid var(--line);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.03);
    padding: 0.72rem 0.8rem;
    display: grid;
    gap: 0.2rem;
  }

  .deck-ai-chat-popup__context span {
    color: var(--muted);
    font-size: 0.74rem;
  }

  .deck-ai-chat-popup__context strong {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .deck-ai-chat-popup__close {
    width: 36px;
    height: 36px;
    border-radius: 12px;
    border: 1px solid var(--line);
    background: var(--surface-input);
    color: var(--ink);
  }

  .deck-ai-chat-popup__targets,
  .deck-ai-chat-popup__quick-prompts {
    display: flex;
    gap: 0.55rem;
    flex-wrap: wrap;
  }

  .deck-ai-chat-popup__targets button {
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-soft);
    color: var(--muted);
    padding: 0.55rem 0.8rem;
  }

  .deck-ai-chat-popup__targets button.active {
    border-color: var(--line-strong);
    background: var(--surface-active);
    color: var(--ink-strong);
  }

  .deck-ai-chat-popup__quick-prompts .pill.active {
    border-color: var(--line-strong);
    background: var(--surface-active);
    color: var(--ink-strong);
  }

  .deck-ai-chat-popup__field {
    display: grid;
    gap: 0.45rem;
  }

  .deck-ai-chat-popup__field span {
    color: var(--muted);
    font-size: 0.88rem;
  }

  .deck-ai-chat-popup__field textarea {
    width: 100%;
    border-radius: 18px;
    border: 1px solid var(--line);
    background: var(--surface-input);
    color: var(--ink);
    padding: 0.9rem 1rem;
  }

  @media (max-width: 720px) {
    .deck-ai-chat-popup {
      right: 1rem;
      bottom: 1rem;
      left: 1rem;
      width: auto;
    }

    .deck-ai-chat-popup__actions {
      flex-wrap: wrap;
    }

    .deck-ai-chat-popup__context {
      grid-template-columns: 1fr;
    }

    .deck-ai-chat-popup__actions .button {
      width: 100%;
      justify-content: center;
    }
  }
</style>
