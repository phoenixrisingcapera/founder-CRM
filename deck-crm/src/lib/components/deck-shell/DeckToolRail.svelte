<script lang="ts">
  import type { DeckShellToolId } from '@deck-aistack-codes/shared';

  interface Props {
    activeTool: DeckShellToolId;
    leftPanelOpen: boolean;
    onSelectTool?: (tool: DeckShellToolId) => void;
    onTogglePanel?: () => void;
  }

  let { activeTool, leftPanelOpen, onSelectTool, onTogglePanel }: Props = $props();

  const toolItems: Array<{ id: DeckShellToolId; label: string; glyph: string }> = [
    { id: 'deck_map', label: 'Deck Map', glyph: 'DM' },
    { id: 'slides', label: 'Slides', glyph: 'SL' },
    { id: 'elements', label: 'Elements', glyph: 'EL' },
    { id: 'text', label: 'Text', glyph: 'TX' },
    { id: 'media', label: 'Media', glyph: 'MD' },
    { id: 'data', label: 'Data', glyph: 'DT' },
    { id: 'ai_tools', label: 'AI Tools', glyph: 'AI' },
    { id: 'brand', label: 'Brand', glyph: 'BR' },
    { id: 'settings', label: 'Settings', glyph: 'ST' }
  ];
</script>

<aside class="deck-tool-rail panel">
  <div class="deck-tool-rail__header">
    <span class="deck-tool-rail__brand">D</span>
    <button
      type="button"
      class="deck-tool-rail__toggle"
      aria-label={leftPanelOpen ? 'Collapse left panel' : 'Expand left panel'}
      onclick={() => onTogglePanel?.()}
    >
      {leftPanelOpen ? '←' : '→'}
    </button>
  </div>

  <nav class="deck-tool-rail__nav" aria-label="Editor tools">
    {#each toolItems as tool}
      <button
        type="button"
        class:selected={tool.id === activeTool}
        class="deck-tool-rail__tool"
        onclick={() => onSelectTool?.(tool.id)}
      >
        <span class="deck-tool-rail__glyph">{tool.glyph}</span>
        <span class="deck-tool-rail__label">{tool.label}</span>
      </button>
    {/each}
  </nav>
</aside>

<style>
  .deck-tool-rail {
    display: grid;
    gap: 0.9rem;
    align-content: start;
    padding: 0.9rem 0.7rem;
  }

  .deck-tool-rail__header {
    display: grid;
    gap: 0.65rem;
    justify-items: center;
  }

  .deck-tool-rail__brand,
  .deck-tool-rail__toggle,
  .deck-tool-rail__glyph {
    display: inline-grid;
    place-items: center;
  }

  .deck-tool-rail__brand {
    width: 44px;
    height: 44px;
    border-radius: 16px;
    background: linear-gradient(135deg, var(--accent), var(--brand-secondary, var(--accent)));
    color: var(--button-primary-ink);
    font-weight: 700;
    box-shadow: var(--shadow-glow-blue);
  }

  .deck-tool-rail__toggle {
    width: 36px;
    height: 36px;
    border-radius: 12px;
    border: 1px solid var(--line);
    background: var(--surface-input);
    color: var(--ink);
  }

  .deck-tool-rail__nav {
    display: grid;
    gap: 0.55rem;
  }

  .deck-tool-rail__tool {
    border: 1px solid var(--line);
    border-radius: 16px;
    background: var(--surface-soft);
    color: var(--muted);
    display: grid;
    gap: 0.45rem;
    justify-items: center;
    padding: 0.75rem 0.35rem;
    min-height: 76px;
  }

  .deck-tool-rail__tool.selected {
    border-color: var(--line-strong);
    background: var(--surface-active);
    color: var(--ink-strong);
    box-shadow: var(--shadow-glow-blue);
  }

  .deck-tool-rail__glyph {
    width: 34px;
    height: 34px;
    border-radius: 12px;
    background: color-mix(in srgb, var(--accent) 14%, var(--surface-input));
    color: var(--accent);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
  }

  .deck-tool-rail__label {
    font-size: 0.72rem;
    line-height: 1.15;
    text-align: center;
  }
</style>
