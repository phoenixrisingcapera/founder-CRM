<script lang="ts">
  import type { DesignVersion, SmartDeckSaveStatus } from '$lib/api/smartDeckWorkspace';

  interface Props {
    activeDesignVersionId?: string | null;
    currentDesignVersionId?: string | null;
    activeVersion?: DesignVersion | null;
    designVersions?: DesignVersion[];
    designViewMode?: 'current' | 'preview' | 'compare';
    saveStatus?: SmartDeckSaveStatus;
    applying?: boolean;
    discarding?: boolean;
    regenerating?: boolean;
    restoring?: boolean;
    onPreviewDesignVersion?: (version: DesignVersion) => void | Promise<void>;
    onApplyDesignVersion?: (versionId: string) => void | Promise<void>;
    onDiscardDesignVersion?: (versionId: string) => void | Promise<void>;
    onRestoreDesignVersion?: (versionId: string) => void | Promise<void>;
    onCompareDesignVersion?: (versionId: string) => void | Promise<void>;
    onShowCurrent?: () => void;
    onRegenerateDesignVersion?: (versionId: string) => void | Promise<void>;
  }

  let {
    activeDesignVersionId = null,
    currentDesignVersionId = null,
    activeVersion = null,
    designVersions = [],
    designViewMode = 'current',
    saveStatus = 'idle',
    applying = false,
    discarding = false,
    regenerating = false,
    restoring = false,
    onPreviewDesignVersion,
    onApplyDesignVersion,
    onDiscardDesignVersion,
    onRestoreDesignVersion,
    onCompareDesignVersion,
    onShowCurrent,
    onRegenerateDesignVersion
  }: Props = $props();

  const visibleVersions = $derived(designVersions.filter((version) => version.status !== 'discarded'));
  const selectedCandidate = $derived(
    activeDesignVersionId && activeDesignVersionId !== currentDesignVersionId
      ? (activeVersion ?? visibleVersions.find((version) => version.id === activeDesignVersionId) ?? null)
      : null
  );
  const isBusy = $derived(applying || discarding || regenerating || restoring || saveStatus === 'saving');
  const isRestorableCandidate = $derived(Boolean(selectedCandidate && selectedCandidate.id !== currentDesignVersionId));

  function versionLabel(index: number) {
    return `Version ${visibleVersions.length - index}`;
  }

  function formatDate(value: string) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function versionDisplayName(version: DesignVersion) {
    const index = visibleVersions.findIndex((item) => item.id === version.id);
    return index >= 0 ? versionLabel(index) : 'selected version';
  }
</script>

<article class="panel generated-batch-save-card">
  <header class="card-header">
    <div>
      <div class="eyebrow">Design versions</div>
      <h2>Review generated iterations</h2>
    </div>
    <span class="pill">{activeVersion?.status ?? `${visibleVersions.length} versions`}</span>
  </header>

  {#if selectedCandidate}
    <section class="preview-action-card" aria-label="Selected design version actions">
      <div class="preview-action-card__copy">
        <strong>Previewing AI design</strong>
        <p>{versionDisplayName(selectedCandidate)} is not saved to the deck until you apply it.</p>
      </div>

      <div class="mode-buttons" aria-label="Deck view mode">
        <button
          type="button"
          class:active={designViewMode === 'current'}
          onclick={() => onShowCurrent?.()}
        >
          Current
        </button>
        <button
          type="button"
          class:active={designViewMode === 'preview'}
          onclick={() => onPreviewDesignVersion?.(selectedCandidate)}
        >
          Preview
        </button>
        <button
          type="button"
          class:active={designViewMode === 'compare'}
          onclick={() => onCompareDesignVersion?.(selectedCandidate.id)}
        >
          Compare
        </button>
      </div>

      <div class="preview-action-card__meta">
        <span>{selectedCandidate.generatedSlides.length} slide{selectedCandidate.generatedSlides.length === 1 ? '' : 's'}</span>
        <span>{formatDate(selectedCandidate.createdAt)}</span>
      </div>

      <div class="actions">
        <button
          class="button secondary"
          type="button"
          disabled={isBusy || !isRestorableCandidate}
          onclick={() => onRestoreDesignVersion?.(selectedCandidate.id)}
        >
          {restoring ? 'Restoring...' : 'Restore version'}
        </button>
        <button
          class="button secondary"
          type="button"
          disabled={isBusy}
          onclick={() => onDiscardDesignVersion?.(selectedCandidate.id)}
        >
          {discarding ? 'Discarding...' : 'Discard'}
        </button>
        <button
          class="button secondary"
          type="button"
          disabled={isBusy}
          onclick={() => onRegenerateDesignVersion?.(selectedCandidate.id)}
        >
          {regenerating ? 'Regenerating...' : 'Regenerate'}
        </button>
        <button
          class="button"
          type="button"
          disabled={isBusy}
          onclick={() => onApplyDesignVersion?.(selectedCandidate.id)}
        >
          {applying || saveStatus === 'saving' ? 'Saving...' : 'Apply to deck'}
        </button>
      </div>
    </section>
  {/if}

  <div class="version-list" aria-label="Generated design versions">
    {#if visibleVersions.length === 0}
      <div class="version-empty">
        <strong>No generated versions yet</strong>
        <span>Generate from selected source slides to create the first reviewable version.</span>
      </div>
    {:else}
      {#each visibleVersions as version, index}
        <button
          type="button"
          class="version-card"
          class:active={version.id === activeDesignVersionId}
          onclick={() => onPreviewDesignVersion?.(version)}
        >
          <div class="version-card__head">
            <strong>{versionLabel(index)}</strong>
            {#if version.id === activeDesignVersionId}
              <span class="pill">{version.id === currentDesignVersionId ? 'Current' : 'Previewing'}</span>
            {:else if version.id === currentDesignVersionId}
              <span class="pill">Saved</span>
            {/if}
          </div>
          <span>{formatDate(version.createdAt)}</span>
          <small>{version.generatedSlides.length} generated slide{version.generatedSlides.length === 1 ? '' : 's'}</small>
          <div class="version-card__thumbs" aria-hidden="true">
            {#each version.generatedSlides.slice(0, 4) as slide}
              {#if slide.previewImageUrl}
                <img src={slide.previewImageUrl} alt="" loading="lazy" />
              {:else}
                <span>{slide.title}</span>
              {/if}
            {/each}
          </div>
        </button>
      {/each}
    {/if}
  </div>
</article>

<style>
  .generated-batch-save-card {
    min-height: 0;
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr);
    gap: 0.95rem;
    padding: 1rem;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
    flex-wrap: wrap;
  }

  h2 {
    margin: 0;
  }

  .preview-action-card {
    display: grid;
    gap: 0.75rem;
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    background: var(--surface-active);
    padding: 0.85rem;
  }

  .preview-action-card__copy {
    display: grid;
    gap: 0.25rem;
  }

  .preview-action-card__copy p {
    margin: 0;
    color: var(--muted);
    font-size: 0.86rem;
  }

  .mode-buttons {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.2rem;
    padding: 0.2rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-soft);
  }

  .mode-buttons button {
    min-width: 0;
    min-height: 2rem;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: var(--muted);
    font-weight: 700;
    cursor: pointer;
  }

  .mode-buttons button.active {
    background: var(--surface);
    color: var(--ink);
    box-shadow: var(--shadow);
  }

  .preview-action-card__meta {
    display: flex;
    justify-content: space-between;
    gap: 0.7rem;
    color: var(--muted);
    font-size: 0.78rem;
  }

  .version-list {
    min-height: 0;
    overflow-y: auto;
    display: grid;
    align-content: start;
    gap: 0.7rem;
  }

  .version-empty,
  .version-card {
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-soft);
    color: inherit;
    padding: 0.8rem;
  }

  .version-empty {
    display: grid;
    gap: 0.35rem;
  }

  .version-empty span,
  .version-card span,
  .version-card small {
    color: var(--muted);
  }

  .version-card {
    width: 100%;
    display: grid;
    gap: 0.4rem;
    text-align: left;
  }

  .version-card.active,
  .version-card:hover,
  .version-card:focus-visible {
    border-color: var(--line-strong);
    background: var(--surface-active);
  }

  .version-card__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.65rem;
  }

  .version-card__thumbs {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.35rem;
  }

  .version-card__thumbs img {
    width: 100%;
    height: 2.6rem;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid var(--line);
    background: var(--surface-input);
  }

  .version-card__thumbs span {
    min-height: 2.6rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--surface-input);
    color: var(--muted);
    display: grid;
    align-content: center;
    overflow: hidden;
    text-overflow: ellipsis;
    padding: 0.35rem;
    font-size: 0.68rem;
  }

  .actions {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.6rem;
  }

  .actions .button {
    width: 100%;
    justify-content: center;
  }

  @media (max-width: 1180px) {
    .actions {
      grid-template-columns: 1fr;
    }
  }
</style>
