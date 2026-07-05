<script lang="ts">
  import type { DeckShellProperties, UpdateDeckShellPropertiesRequest } from '@deck-aistack-codes/shared';
  import SaveConfirmationBanner from '$lib/components/deckService/feedback/SaveConfirmationBanner.svelte';
  import type { SaveConfirmationBannerModel } from '$lib/contracts/types';
  import type { AnalysisFinding, AdaptationSuggestion, BlockClassification, Deck, DeckSlide, DeckSlideBlock, DeckSlideRevision } from '$types/domain';

  interface Props {
    deck: Deck;
    properties?: DeckShellProperties;
    slides: DeckSlide[];
    blocks: DeckSlideBlock[];
    classifications: BlockClassification[];
    findings: AnalysisFinding[];
    suggestions: AdaptationSuggestion[];
    revisions: DeckSlideRevision[];
    open?: boolean;
    isSaving?: boolean;
    saveConfirmation?: SaveConfirmationBannerModel | null;
    onSave?: (payload: UpdateDeckShellPropertiesRequest) => void;
  }

  let {
    deck,
    properties,
    slides,
    blocks,
    classifications,
    findings,
    suggestions,
    revisions,
    open = false,
    isSaving = false,
    saveConfirmation = null,
    onSave
  }: Props = $props();

  let companyName = $state('');
  let companyWebsiteUrl = $state('');
  let founderName = $state('');
  let audienceLabel = $state('');
  let primaryGoal = $state('');
  let brandSummary = $state('');
  let visualDirection = $state('');
  let teamSummary = $state('');

  $effect(() => {
    companyName = properties?.companyName ?? deck.title;
    companyWebsiteUrl = properties?.companyWebsiteUrl ?? '';
    founderName = properties?.founderName ?? '';
    audienceLabel = properties?.audienceLabel ?? deck.audience;
    primaryGoal = properties?.primaryGoal ?? deck.purpose;
    brandSummary = properties?.brandSummary ?? '';
    visualDirection = properties?.visualDirection ?? '';
    teamSummary = properties?.teamSummary ?? '';
  });

  const roleCounts = $derived(
    slides.reduce<Record<string, number>>((counts, slide) => {
      counts[slide.role] = (counts[slide.role] ?? 0) + 1;
      return counts;
    }, {})
  );

  const topRoles = $derived(
    Object.entries(roleCounts)
      .sort((left, right) => right[1] - left[1])
      .slice(0, 5)
  );

  const highRiskFindings = $derived(findings.filter((finding) => finding.severity === 'high').length);
  const acceptedSuggestions = $derived(suggestions.filter((suggestion) => suggestion.status === 'accepted').length);
  const classifiedBlocks = $derived(classifications.length);
  const fileTypeLabel = $derived(deck.file?.mimeType?.split('/').at(-1)?.toUpperCase() ?? 'Unknown');
  const brandAssetLabels = $derived(properties?.brandAssetLabels ?? []);

  function saveForm() {
    onSave?.({
      companyName: companyName.trim() || null,
      companyWebsiteUrl: companyWebsiteUrl.trim() || null,
      founderName: founderName.trim() || null,
      audienceLabel: audienceLabel.trim() || null,
      primaryGoal: primaryGoal.trim() || null,
      brandSummary: brandSummary.trim() || null,
      visualDirection: visualDirection.trim() || null,
      teamSummary: teamSummary.trim() || null
    });
  }
</script>

<aside class:open={open} class="properties-drawer panel" aria-hidden={!open}>
  <div class="properties-drawer__header">
    <div>
      <div class="eyebrow">Deck properties</div>
      <h3>{deck.title}</h3>
    </div>
    <span class="pill">{deck.status}</span>
  </div>

  <section class="properties-drawer__section">
    <div class="section-head">
      <strong>Company context</strong>
      <span class="pill">{properties?.processingStatus ?? 'draft'}</span>
    </div>
    <div class="properties-drawer__form-grid">
      <label>
        <span>Company name</span>
        <input bind:value={companyName} placeholder="Company name" />
      </label>
      <label>
        <span>Company website</span>
        <input bind:value={companyWebsiteUrl} placeholder="https://company.com" />
      </label>
      <label>
        <span>Founder name</span>
        <input bind:value={founderName} placeholder="Founder or CEO" />
      </label>
      <label>
        <span>Audience</span>
        <input bind:value={audienceLabel} placeholder="Investment Committee" />
      </label>
      <label class="properties-drawer__wide">
        <span>Primary goal</span>
        <input bind:value={primaryGoal} placeholder="What should this deck accomplish?" />
      </label>
      <label class="properties-drawer__wide">
        <span>Brand summary</span>
        <textarea bind:value={brandSummary} rows="3" placeholder="Describe the company brand and tone the shell should preserve."></textarea>
      </label>
      <label class="properties-drawer__wide">
        <span>Visual direction</span>
        <textarea bind:value={visualDirection} rows="3" placeholder="Describe how the next versions should feel visually."></textarea>
      </label>
      <label class="properties-drawer__wide">
        <span>Team summary</span>
        <textarea bind:value={teamSummary} rows="3" placeholder="Summarise the team context used in the deck narrative."></textarea>
      </label>
    </div>

    <div class="properties-drawer__actions">
      <button type="button" class="button" onclick={saveForm} disabled={isSaving}>
        {isSaving ? 'Saving...' : 'Save deck properties'}
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

    <div class="summary-grid">
      <article>
        <span>Stage</span>
        <strong>{properties?.companyStage ?? 'Not inferred yet'}</strong>
      </article>
      <article>
        <span>Contact email</span>
        <strong>{properties?.contactEmail ?? 'Not detected yet'}</strong>
      </article>
    </div>
  </section>

  <section class="properties-drawer__section">
    <strong>Source file</strong>
    <dl>
      <div>
        <dt>Uploaded file</dt>
        <dd>{properties?.sourceFileName ?? deck.file?.filename ?? 'Pending upload'}</dd>
      </div>
      <div>
        <dt>File type</dt>
        <dd>{fileTypeLabel}</dd>
      </div>
      <div>
        <dt>Brand ready</dt>
        <dd>{properties?.brandReady ? 'Yes' : 'Not yet'}</dd>
      </div>
      <div>
        <dt>Last updated</dt>
        <dd>{properties?.updatedAt ? new Date(properties.updatedAt).toLocaleString() : 'Not saved yet'}</dd>
      </div>
    </dl>
  </section>

  <section class="properties-drawer__section">
    <strong>Sources used</strong>
    {#if properties?.sourcesUsed?.length}
      <div class="tag-row">
        {#each properties.sourcesUsed as sourceLabel}
          <span class="pill">{sourceLabel}</span>
        {/each}
      </div>
    {:else}
      <p class="muted">No supplemental sources have been recorded for this deck yet.</p>
    {/if}
  </section>

  <section class="properties-drawer__section">
    <strong>Brand assets</strong>
    {#if brandAssetLabels.length}
      <div class="tag-row">
        {#each brandAssetLabels as assetLabel}
          <span class="pill">{assetLabel}</span>
        {/each}
      </div>
    {:else}
      <p class="muted">No brand guide or logo files have been attached to this deck yet.</p>
    {/if}
  </section>

  <section class="properties-drawer__section">
    <strong>Deck structure</strong>
    <div class="summary-grid">
      <article>
        <span>Slides</span>
        <strong>{slides.length}</strong>
      </article>
      <article>
        <span>Editable blocks</span>
        <strong>{blocks.length}</strong>
      </article>
      <article>
        <span>Classified blocks</span>
        <strong>{classifiedBlocks}</strong>
      </article>
      <article>
        <span>Revisions</span>
        <strong>{revisions.length}</strong>
      </article>
    </div>
  </section>

  <section class="properties-drawer__section">
    <strong>Detected sections</strong>
    <div class="tag-row">
      {#each topRoles as [role, count]}
        <span class="pill">{role.replaceAll('_', ' ')} · {count}</span>
      {/each}
    </div>
  </section>

  <section class="properties-drawer__section">
    <strong>Review health</strong>
    <div class="summary-grid">
      <article>
        <span>Findings</span>
        <strong>{findings.length}</strong>
      </article>
      <article>
        <span>High risk</span>
        <strong>{highRiskFindings}</strong>
      </article>
      <article>
        <span>Suggestions</span>
        <strong>{suggestions.length}</strong>
      </article>
      <article>
        <span>Accepted</span>
        <strong>{acceptedSuggestions}</strong>
      </article>
    </div>
  </section>
</aside>

<style>
  .properties-drawer {
    position: sticky;
    top: 1rem;
    display: none;
    gap: 1rem;
    padding: 1.1rem;
    align-content: start;
  }

  .properties-drawer.open {
    display: grid;
  }

  .properties-drawer__header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
  }

  .properties-drawer__header h3 {
    margin: 0.35rem 0 0;
  }

  .properties-drawer__section {
    display: grid;
    gap: 0.7rem;
  }

  .properties-drawer__form-grid {
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .properties-drawer__form-grid label {
    display: grid;
    gap: 0.35rem;
  }

  .properties-drawer__form-grid span {
    color: var(--muted);
    font-size: 0.84rem;
  }

  .properties-drawer__form-grid input,
  .properties-drawer__form-grid textarea {
    width: 100%;
    border-radius: 16px;
    border: 1px solid var(--line);
    background: var(--surface-input);
    color: var(--ink);
    padding: 0.8rem 0.9rem;
  }

  .properties-drawer__wide {
    grid-column: 1 / -1;
  }

  .properties-drawer__actions {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: wrap;
  }

  dl,
  .summary-grid {
    display: grid;
    gap: 0.75rem;
  }

  dl div,
  .summary-grid article {
    border: 1px solid var(--line);
    border-radius: 16px;
    background: var(--surface-soft);
    padding: 0.8rem 0.9rem;
  }

  dt,
  .summary-grid span {
    color: var(--muted);
    font-size: 0.84rem;
  }

  dd,
  .summary-grid strong {
    margin: 0.2rem 0 0;
    font-weight: 600;
  }

  .tag-row {
    display: flex;
    gap: 0.55rem;
    flex-wrap: wrap;
  }

  @media (max-width: 1200px) {
    .properties-drawer {
      position: static;
    }
  }

  @media (max-width: 720px) {
    .properties-drawer__form-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
