<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import InteractiveDeckShell from '$components/InteractiveDeckShell.svelte';
  import LlmParallelizationCard from '$lib/components/smart-deck/LlmParallelizationCard.svelte';
  import SmartDeckWorkspace from '$lib/components/smart-deck/SmartDeckWorkspace.svelte';
  import SourceEnrichmentStatusCard from '$lib/components/smart-deck/SourceEnrichmentStatusCard.svelte';
  import type { PageData } from './$types';

  type SourceAsset = {
    assetType?: string;
    assetUrl?: string | null;
    label?: string | null;
    mimeType?: string | null;
  };
  type SourceBlock = {
    id?: string;
    blockKind?: string | null;
    semanticRole?: string | null;
    enrichmentSource?: string | null;
  };
  type SourceSlide = {
    slideIndex: number;
    title?: string | null;
    semanticSlideType?: string | null;
    enrichmentSource?: string | null;
    blocks?: SourceBlock[];
    assets?: SourceAsset[];
  };
  type SourceInspectionView = {
    structure?: {
      slides?: SourceSlide[];
      extractionRun?: {
        slideCount?: number;
        blockCount?: number;
        sourceEnrichment?: unknown;
      };
      sourceEnrichment?: unknown;
    } | null;
  };

  let { data }: { data: PageData } = $props();
  const sourceInspection = $derived((data.sourceInspection ?? null) as SourceInspectionView | null);
  const sourceSlides = $derived(
    Array.isArray(sourceInspection?.structure?.slides) ? sourceInspection.structure.slides.slice(0, 4) : []
  );
  const sourceMediaAssets = $derived(
    (sourceSlides as SourceSlide[])
      .flatMap((slide: SourceSlide) =>
        Array.isArray(slide.assets)
          ? slide.assets.map((asset: SourceAsset) => ({
              ...asset,
              slideIndex: slide.slideIndex
            }))
          : []
      )
      .filter((asset: SourceAsset & { slideIndex: number }) => asset.assetType === 'embedded_image' && typeof asset.assetUrl === 'string')
      .slice(0, 4)
  );
  const sourceSlideCount = $derived(
    typeof sourceInspection?.structure?.extractionRun?.slideCount === 'number'
      ? sourceInspection.structure.extractionRun.slideCount
      : sourceSlides.length
  );
  const sourceBlockCount = $derived(
    typeof sourceInspection?.structure?.extractionRun?.blockCount === 'number'
      ? sourceInspection.structure.extractionRun.blockCount
      : (sourceSlides as SourceSlide[]).reduce((total, slide) => total + (slide.blocks?.length ?? 0), 0)
  );
  const sourceEnrichment = $derived(
    sourceInspection?.structure?.sourceEnrichment ?? sourceInspection?.structure?.extractionRun?.sourceEnrichment ?? null
  );
  const packageMetadata = $derived(data.smartDeckWorkspace?.knowledgeMetadata ?? null);
  const runtimeContext = $derived(data.smartDeckWorkspace?.runtimeContext ?? null);
  const runtimeCapabilities = $derived(data.smartDeckWorkspace?.runtimeCapabilities ?? null);
  const runtimeCapabilityTasks = $derived(runtimeCapabilities?.llmTasks?.slice(0, 5) ?? []);
  const runtimeGuardrailGroups = $derived(runtimeCapabilities?.guardrailGroups?.slice(0, 4) ?? []);
  const enabledCapabilities = $derived(runtimeCapabilities?.enabledSmartDeckCapabilities?.slice(0, 8) ?? []);
  const sparkSourceSlideIds = $derived(
    data.smartDeckWorkspace?.preferences.selectedSourceSlideIds?.length
      ? data.smartDeckWorkspace.preferences.selectedSourceSlideIds
      : data.smartDeckWorkspace?.sourceSlides.map((slide: { id: string }) => slide.id) ?? []
  );
  const sparkPreferredModel = $derived(data.smartDeckWorkspace?.preferences.preferredModel ?? null);
</script>

<AppShell
  title="Smart Deck"
  subtitle={`${data.graph.deck.audience} - ${data.graph.deck.purpose}`}
  status={data.graph.deck.status}
  deckLabel={data.graph.deck.title}
  currentDeckId={data.graph.deck.id}
  latestBatches={data.latestBatches}
  activeNav="smart-deck"
  compactSidebar={true}
  compactTopBar={true}
  showTopBarSearch={false}
>
  {#snippet actions()}
    <a class="button secondary" href={`/decks/${data.graph.deck.id}/smart-edit?slide=${data.selectedSlideId}`}>Smart Edit</a>
    <a class="button secondary" href={`/decks/${data.graph.deck.id}/due-diligence`}>Due Diligence</a>
    <a class="button secondary" href={`/decks/${data.graph.deck.id}/export`}>Export</a>
  {/snippet}

  {#if sourceSlides.length > 0}
    <SourceEnrichmentStatusCard enrichment={sourceEnrichment} slideCount={sourceSlideCount} blockCount={sourceBlockCount} />

    <section class="source-inspection" aria-label="Persisted source structure">
      <div class="source-summary">
        <div>
          <p class="eyebrow">Source structure</p>
          <h2>{sourceSlideCount} persisted slides</h2>
        </div>
        <span>{sourceMediaAssets.length} embedded media previews</span>
      </div>
      <div class="source-slide-list">
        {#each sourceSlides as slide}
          <article>
            <strong>{slide.slideIndex}. {slide.title}</strong>
            <small>{slide.blocks?.length ?? 0} blocks · {slide.assets?.length ?? 0} assets</small>
            <div class="source-chip-row">
              {#if slide.semanticSlideType}
                <span>{slide.semanticSlideType}</span>
              {/if}
              {#if slide.enrichmentSource}
                <span>{slide.enrichmentSource}</span>
              {/if}
            </div>
            {#if slide.blocks?.length}
              <div class="block-chip-row" aria-label="Source block labels">
                {#each slide.blocks.slice(0, 3) as block}
                  <span>{block.blockKind ?? 'block'} · {block.semanticRole ?? 'supporting_text'}</span>
                {/each}
              </div>
            {/if}
          </article>
        {/each}
      </div>
      {#if sourceMediaAssets.length > 0}
        <div class="media-list" aria-label="Persisted embedded media assets">
          {#each sourceMediaAssets as asset}
            <a href={asset.assetUrl} target="_blank" rel="noreferrer">
              <span>{asset.label ?? 'Embedded image'}</span>
              <small>Slide {asset.slideIndex} · {asset.mimeType ?? 'image'}</small>
            </a>
          {/each}
        </div>
      {/if}
    </section>
  {/if}

  {#if packageMetadata || runtimeContext || runtimeCapabilities}
    <section class="source-inspection" aria-label="Runtime package context">
      <div class="source-summary">
        <div>
          <p class="eyebrow">LLM runtime</p>
          <h2>{runtimeCapabilities?.knowledgeMetadata?.name ?? packageMetadata?.name ?? 'Loaded package context'}</h2>
        </div>
        <span>
          {runtimeCapabilities?.knowledgeMetadata?.version ?? packageMetadata?.version ?? 'unknown'}
          · {runtimeCapabilities?.schemaVersion ?? runtimeContext?.schemaVersion ?? 'runtime-context'}
        </span>
      </div>
      <div class="artifact-list">
        {#if runtimeCapabilities?.knowledgeMetadata || packageMetadata}
          <span>{runtimeCapabilities?.knowledgeMetadata?.moduleCount ?? packageMetadata?.moduleCount ?? 0} knowledge modules</span>
          <span>{runtimeCapabilities?.knowledgeMetadata?.source ?? packageMetadata?.source ?? 'compiled_json'}</span>
        {/if}
        {#if runtimeContext}
          <span>{runtimeContext.productObjects?.length ?? 0} product objects</span>
          <span>{runtimeContext.allowedCommands?.length ?? 0} allowed commands</span>
        {/if}
        {#if runtimeCapabilities}
          <span>{runtimeCapabilityTasks.length} task routes</span>
          <span>{runtimeGuardrailGroups.length} guardrail groups</span>
        {/if}
      </div>

      {#if runtimeCapabilityTasks.length > 0}
        <div class="runtime-grid" aria-label="LLM task routes">
          {#each runtimeCapabilityTasks as task}
            <article>
              <strong>{task.key.replaceAll('_', ' ')}</strong>
              <small>{task.inputs.length} inputs · {task.outputs.length} outputs</small>
            </article>
          {/each}
        </div>
      {/if}

      {#if enabledCapabilities.length > 0 || runtimeGuardrailGroups.length > 0}
        <div class="runtime-grid" aria-label="Runtime guardrails">
          {#each enabledCapabilities as capability}
            <article>
              <strong>{capability.replaceAll('_', ' ')}</strong>
              <small>enabled capability</small>
            </article>
          {/each}
          {#each runtimeGuardrailGroups as group}
            <article>
              <strong>{group.group}</strong>
              <small>{group.rules.length} rules</small>
            </article>
          {/each}
        </div>
      {/if}
    </section>
  {/if}

  {#if data.smartDeckWorkspace && sparkSourceSlideIds.length > 0}
    <LlmParallelizationCard
      deckId={data.graph.deck.id}
      selectedSourceSlideIds={sparkSourceSlideIds}
      preferredModel={sparkPreferredModel}
    />
  {/if}

  {#if data.smartDeckWorkspace}
    <SmartDeckWorkspace initialWorkspace={data.smartDeckWorkspace} initialPreviewDesignVersionId={data.previewDesignVersionId} />
  {:else}
    <InteractiveDeckShell
      graph={data.graph}
      workspaceModel={data.workspaceModel}
      properties={data.properties}
      workspacePreferences={data.workspacePreferences}
      selectedSlideId={data.selectedSlideId}
      latestBatches={data.latestBatches}
      latestConfirmation={data.latestConfirmation}
      workspaceHrefBase={`/decks/${data.graph.deck.id}/smart-deck`}
      backHref="/decks"
      backLabel="Decks"
    />
  {/if}
</AppShell>

<style>
  .source-inspection {
    display: grid;
    gap: 0.75rem;
    margin-bottom: 1rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    background: var(--surface);
  }

  .source-summary,
  .source-slide-list,
  .media-list,
  .runtime-grid {
    display: grid;
    gap: 0.75rem;
  }

  .source-summary {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
  }

  .source-summary h2,
  .source-summary p {
    margin: 0;
  }

  .source-summary span,
  .source-slide-list small,
  .media-list small,
  .runtime-grid small {
    color: var(--text-muted);
  }

  .source-slide-list,
  .runtime-grid {
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }

  .source-slide-list article,
  .media-list a,
  .runtime-grid article {
    min-width: 0;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.65rem;
    background: var(--surface-subtle);
  }

  .source-chip-row,
  .block-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  .source-chip-row span,
  .block-chip-row span {
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.2rem 0.45rem;
    color: var(--text-muted);
    font-size: 0.76rem;
  }

  .source-slide-list article,
  .runtime-grid article,
  .runtime-grid article {
    display: grid;
    gap: 0.25rem;
  }

  .media-list a {
    display: grid;
    gap: 0.25rem;
    color: var(--text);
    text-decoration: none;
  }

  .source-slide-list strong,
  .media-list span,
  .media-list small,
  .runtime-grid strong,
  .runtime-grid small,
  .runtime-grid small {
    overflow-wrap: anywhere;
  }

  .media-list,
  .runtime-grid {
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }

  @media (max-width: 720px) {
    .source-summary {
      grid-template-columns: 1fr;
    }
  }
</style>
