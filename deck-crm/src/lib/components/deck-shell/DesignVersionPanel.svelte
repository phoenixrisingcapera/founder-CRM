<script lang="ts">
  import type { GeneratedSlideVersion } from '@deck-aistack-codes/shared';

  interface Props {
    versions?: GeneratedSlideVersion[];
    isSubmitting?: boolean;
    onAccept?: (versionId: string, sourceSlideId: string | null) => void;
    onReject?: (versionId: string, sourceSlideId: string | null) => void;
  }

  let { versions = [], isSubmitting = false, onAccept, onReject }: Props = $props();
</script>

<section class="design-version-panel">
  <div class="section-head">
    <strong>Generated versions</strong>
    <span class="muted">{versions.length} for this slide</span>
  </div>

  {#if versions.length > 0}
    <div class="design-version-panel__stack">
      {#each versions as version}
        <article class="design-version-panel__version">
          <div class="section-head">
            <strong>{version.title}</strong>
            <span class="pill">{version.status}</span>
          </div>
          <p class="muted">Version {version.versionNumber} · Slide {String(version.slideIndex).padStart(2, '0')}</p>
          <div class="design-version-panel__layout">
            {#each version.generatedSlide.blocks as block}
              <div class="design-version-panel__block">
                <span class="pill">{block.type}</span>
                <strong>{block.text}</strong>
                <p class="muted">{block.role}</p>
              </div>
            {/each}
          </div>
          <p class="muted">{version.generatedSlide.designRationale}</p>
          <div class="design-version-panel__actions">
            <button
              type="button"
              class="button"
              onclick={() => onAccept?.(version.id, version.sourceSlideId)}
              disabled={isSubmitting || version.status !== 'reviewable'}
            >
              Accept version
            </button>
            <button
              type="button"
              class="button secondary"
              onclick={() => onReject?.(version.id, version.sourceSlideId)}
              disabled={isSubmitting || version.status !== 'reviewable'}
            >
              Keep original
            </button>
          </div>
        </article>
      {/each}
    </div>
  {:else}
    <p class="muted">Generated versions will appear here after the LLM design shell returns structured slide JSON for the selected slide.</p>
  {/if}
</section>

<style>
  .design-version-panel {
    display: grid;
    gap: 0.9rem;
  }

  .design-version-panel__stack,
  .design-version-panel__layout {
    display: grid;
    gap: 0.75rem;
  }

  .design-version-panel__version {
    border: 1px solid var(--line);
    border-radius: 22px;
    background: var(--surface-muted);
    padding: 1rem;
  }

  .design-version-panel__version p {
    margin: 0.55rem 0 0;
    line-height: 1.6;
  }

  .design-version-panel__block {
    display: grid;
    gap: 0.35rem;
    padding: 0.8rem;
    border-radius: 16px;
    border: 1px solid var(--line);
    background: var(--surface-input);
  }

  .design-version-panel__actions {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-top: 0.75rem;
  }
</style>
