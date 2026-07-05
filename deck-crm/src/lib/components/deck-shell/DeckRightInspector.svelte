<script lang="ts">
  import SaveConfirmationBanner from '$lib/components/deckService/feedback/SaveConfirmationBanner.svelte';
  import type { SaveConfirmationBannerModel } from '$lib/contracts/types';
  import type { AdaptationSuggestion, AnalysisFinding, BlockClassification, DeckSlide, DeckSlideBlock } from '$types/domain';

  interface Props {
    slide?: DeckSlide;
    block?: DeckSlideBlock;
    classification?: BlockClassification;
    relatedFindings?: AnalysisFinding[];
    relatedSuggestions?: AdaptationSuggestion[];
    isSaving?: boolean;
    saveConfirmation?: SaveConfirmationBannerModel | null;
    onSave?: (text: string) => void;
  }

  let {
    slide,
    block,
    classification,
    relatedFindings = [],
    relatedSuggestions = [],
    isSaving = false,
    saveConfirmation = null,
    onSave
  }: Props = $props();

  let activeTab = $state<'design' | 'animate' | 'data'>('design');
  let draftText = $state('');

  // Keep the inspector draft aligned with the currently selected block.
  $effect(() => {
    draftText = block?.rawText ?? '';
  });

  const blockLabel = $derived(block ? block.blockType.replaceAll('_', ' ') : 'No block selected');
  const classificationLabel = $derived(
    classification ? `${classification.semanticTag} · ${classification.diligenceCategory}` : 'Content tag pending'
  );

  function saveBlockText() {
    if (!block || !draftText.trim()) return;
    onSave?.(draftText.trim());
  }
</script>

<aside class="deck-right-inspector panel">
  <div class="deck-right-inspector__header">
    <div>
      <div class="eyebrow">Inspector</div>
      <h3>{block ? 'Selected block' : 'Select a block'}</h3>
    </div>
    {#if slide}
      <span class="pill">Slide {String(slide.slideIndex).padStart(2, '0')}</span>
    {/if}
  </div>

  {#if block}
    <div class="deck-right-inspector__tabs">
      <button type="button" class:active={activeTab === 'design'} onclick={() => (activeTab = 'design')}>Design</button>
      <button type="button" class:active={activeTab === 'animate'} onclick={() => (activeTab = 'animate')}>Animate</button>
      <button type="button" class:active={activeTab === 'data'} onclick={() => (activeTab = 'data')}>Data</button>
    </div>

    {#if activeTab === 'design'}
      <section class="deck-right-inspector__card">
        <div class="section-head">
          <strong>{blockLabel}</strong>
          <span class="muted">{classificationLabel}</span>
        </div>

        <label class="deck-right-inspector__field">
          <span>Content</span>
          <textarea
            bind:value={draftText}
            rows="8"
            placeholder="Refine the selected block text here."
          ></textarea>
        </label>

        <div class="deck-right-inspector__summary">
          <article>
            <span>Element</span>
            <strong>{blockLabel}</strong>
          </article>
          <article>
            <span>Text length</span>
            <strong>{draftText.length} chars</strong>
          </article>
          <article>
            <span>Spacing</span>
            <strong>{block.blockType === 'headline' ? 'Tight headline' : 'Readable body'}</strong>
          </article>
          <article>
            <span>Emphasis</span>
            <strong>{block.blockType === 'metric' ? 'Numeric highlight' : 'Editorial'}</strong>
          </article>
        </div>

        <div class="deck-right-inspector__actions">
          <button type="button" class="button" onclick={saveBlockText} disabled={isSaving || !draftText.trim()}>
            {isSaving ? 'Saving block...' : 'Save block'}
          </button>
          {#if saveConfirmation}
            <SaveConfirmationBanner
              title={saveConfirmation.title}
              message={saveConfirmation.message}
              tone={saveConfirmation.tone}
              compact={true}
            />
          {/if}
        </div>
      </section>
    {/if}

    {#if activeTab === 'animate'}
      <section class="deck-right-inspector__card">
        <div class="section-head">
          <strong>Motion guidance</strong>
          <span class="pill">Manual review</span>
        </div>
        <p class="muted">
          Motion stays optional and reviewable. Keep transitions restrained so investor-facing slides feel calm, clear, and premium.
        </p>
        <div class="deck-right-inspector__summary">
          <article>
            <span>Entrance</span>
            <strong>{block.blockType === 'headline' ? 'Fade up' : 'Appear on click'}</strong>
          </article>
          <article>
            <span>Timing</span>
            <strong>Subtle</strong>
          </article>
        </div>
      </section>
    {/if}

    {#if activeTab === 'data'}
      <section class="deck-right-inspector__card">
        <div class="section-head">
          <strong>Context</strong>
          <span class="muted">{classificationLabel}</span>
        </div>
        <div class="deck-right-inspector__summary">
          <article>
            <span>Slide</span>
            <strong>{slide?.title ?? 'Current slide'}</strong>
          </article>
          <article>
            <span>Confidence</span>
            <strong>{classification ? classification.confidence.toFixed(2) : 'Pending'}</strong>
          </article>
          <article>
            <span>Findings</span>
            <strong>{relatedFindings.length}</strong>
          </article>
          <article>
            <span>Recommendations</span>
            <strong>{relatedSuggestions.length}</strong>
          </article>
        </div>

        {#if relatedFindings.length > 0}
          <div class="deck-right-inspector__stack">
            {#each relatedFindings.slice(0, 2) as finding}
              <article class="deck-right-inspector__note">
                <strong>{finding.title}</strong>
                <p>{finding.detail}</p>
              </article>
            {/each}
          </div>
        {/if}
      </section>
    {/if}
  {:else}
    <section class="deck-right-inspector__empty">
      <strong>No block selected</strong>
      <p class="muted">Click a headline, paragraph, quote, or metric on the canvas to inspect and refine it here.</p>
    </section>
  {/if}
</aside>

<style>
  .deck-right-inspector {
    display: grid;
    gap: 1rem;
    align-content: start;
    padding: 1rem;
  }

  .deck-right-inspector__header,
  .deck-right-inspector__actions {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
  }

  .deck-right-inspector__header h3 {
    margin: 0.2rem 0 0;
  }

  .deck-right-inspector__tabs {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .deck-right-inspector__tabs button {
    border: 1px solid var(--line);
    border-radius: 16px;
    background: var(--surface-soft);
    color: var(--muted);
    padding: 0.75rem 0.8rem;
  }

  .deck-right-inspector__tabs button.active {
    border-color: var(--line-strong);
    background: var(--surface-active);
    color: var(--ink-strong);
  }

  .deck-right-inspector__card,
  .deck-right-inspector__empty {
    border: 1px solid var(--line);
    border-radius: 24px;
    background: var(--surface-soft);
    padding: 1rem;
    display: grid;
    gap: 0.9rem;
  }

  .deck-right-inspector__field {
    display: grid;
    gap: 0.45rem;
  }

  .deck-right-inspector__field span {
    color: var(--muted);
    font-size: 0.88rem;
  }

  .deck-right-inspector__field textarea {
    width: 100%;
    border-radius: 18px;
    border: 1px solid var(--line);
    background: var(--surface-input);
    color: var(--ink);
    padding: 0.9rem 1rem;
    resize: vertical;
  }

  .deck-right-inspector__summary {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
  }

  .deck-right-inspector__summary article,
  .deck-right-inspector__note {
    border: 1px solid var(--line);
    border-radius: 18px;
    background: var(--surface-muted);
    padding: 0.9rem;
    display: grid;
    gap: 0.3rem;
  }

  .deck-right-inspector__summary span {
    color: var(--muted);
    font-size: 0.82rem;
  }

  .deck-right-inspector__stack {
    display: grid;
    gap: 0.7rem;
  }

  .deck-right-inspector__note p {
    margin: 0;
    line-height: 1.5;
  }
</style>
