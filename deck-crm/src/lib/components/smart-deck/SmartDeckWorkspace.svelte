<script lang="ts">
  import { goto } from '$app/navigation';
  import type { GeneratedSlide, GeneratedSlideBlock } from '@deck-aistack-codes/shared';
  import {
    type GeneratedSlideCode,
    type DesignVersion,
    type SmartDeckWorkspacePayload,
    type SmartDeckSaveStatus,
    type SmartDeckGenerationInput,
    startSmartDeckGenerationWorkflow,
    waitForWorkflowJobCompletion,
    getSmartDeckWorkspace,
    getGeneratedSlideCode,
    createElementVariationJob,
    applyDesignVersion,
    discardDesignVersion,
    restoreDesignVersion,
    updateSmartDeckSelection,
    patchSmartDeckPreferences
  } from '$lib/api/smartDeckWorkspace';
  import type { SmartDeckDeckType, SmartDeckSubject } from '$lib/types/smart-deck-subjects';
  import DeckDesignShellCard from './DeckDesignShellCard.svelte';
  import GeneratedBatchSaveCard from './GeneratedBatchSaveCard.svelte';
  import LlmChatCard from './LlmChatCard.svelte';
  import PdfSlideMiniaturesCard from './PdfSlideMiniaturesCard.svelte';

  interface Props {
    initialWorkspace: SmartDeckWorkspacePayload;
    initialPreviewDesignVersionId?: string | null;
  }

  type DesignViewMode = 'current' | 'preview' | 'compare';

  let { initialWorkspace, initialPreviewDesignVersionId = null }: Props = $props();

  function initialSelectedSourceSlideIds(value: SmartDeckWorkspacePayload) {
    if (value.preferences.selectedSourceSlideIds?.length) return value.preferences.selectedSourceSlideIds;
    if (value.sourceSlides[0]?.id) return [value.sourceSlides[0].id];
    return [];
  }

  function initialActiveSourceSlideId(value: SmartDeckWorkspacePayload) {
    return value.activeSourceSlideId ?? value.preferences.activeSourceSlideId ?? value.sourceSlides[0]?.id ?? null;
  }

  function initialActiveGeneratedSlideId(value: SmartDeckWorkspacePayload) {
    return value.activeGeneratedSlideId ?? value.preferences.activeGeneratedSlideId ?? value.generatedSlides[0]?.id ?? null;
  }

  function initialSelectedDesignVersionId(value: SmartDeckWorkspacePayload, requestedPreviewId: string | null) {
    const currentVersion = currentVersionForWorkspace(value);
    const requestedPreview = requestedPreviewId
      ? value.designVersions.find((version) => version.id === requestedPreviewId && version.status !== 'discarded')
      : null;
    if (requestedPreview && requestedPreview.id !== currentVersion?.id) return requestedPreview.id;

    const persistedPreviewId = value.activeDesignVersionId ?? value.preferences.activeDesignVersionId ?? null;
    const persistedPreview = persistedPreviewId
      ? value.designVersions.find((version) => version.id === persistedPreviewId && version.status !== 'discarded')
      : null;
    if (persistedPreview && persistedPreview.id !== currentVersion?.id) return persistedPreview.id;

    const latestPreview = value.designVersions.find((version) => {
      const status = version.status.toLowerCase();
      return version.id !== currentVersion?.id && status !== 'discarded' && status !== 'archived' && !version.isActive;
    });
    return latestPreview?.id ?? currentVersion?.id ?? null;
  }

  function generatedSlideFromBackend(slide: SmartDeckWorkspacePayload['generatedSlides'][number]) {
    const renderSchema = slide.renderSchema as unknown as GeneratedSlideCode['renderSchema'];
    return {
      id: slide.id,
      slideType: (['cover', 'problem', 'solution', 'market', 'product', 'traction', 'business_model', 'ask'][
        Math.max(0, slide.slideNumber - 1) % 8
      ] ?? 'generic') as GeneratedSlide['slideType'],
      status: (slide.validationStatus === 'valid' ? 'ok' : 'needs_review') as GeneratedSlide['status'],
      title: slide.title,
      layout: {
        canvas: '16:9' as const,
        composition: 'simple_text' as const,
        safeMarginPx: 64
      },
      blocks: renderSchema.elements.map((element) => ({
        id: element.id,
        type: (element.type === 'text' ? 'body' : element.type === 'image' ? 'image_placeholder' : 'shape') as GeneratedSlideBlock['type'],
        text: element.text ?? element.type,
        role: (element.type === 'shape' ? 'decorative' : 'primary') as GeneratedSlideBlock['role'],
        x: element.x,
        y: element.y,
        w: element.width,
        h: element.height
      })),
      speakerNotes: 'Generated from selected source PDF slides and stored as backend render_schema_json.',
      designRationale: 'Rendered from the persisted Smart Deck render schema.',
      qualityFlags:
        (slide.validationStatus === 'valid' ? ['ok'] : ['needs_human_review']) as GeneratedSlide['qualityFlags']
    };
  }

  let initialized = false;
  let workspace = $state<SmartDeckWorkspacePayload | null>(null);
  let selectedSourceSlideIds = $state<string[]>([]);
  let activeSourceSlideId = $state<string | null>(null);
  let activeGeneratedSlideId = $state<string | null>(null);
  let selectedDesignVersionId = $state<string | null>(null);
  let selectedElementId = $state<string | null>(null);
  let generatedSlideCode = $state<GeneratedSlideCode | null>(null);
  let currentGeneratedSlideCode = $state<GeneratedSlideCode | null>(null);
  let designViewMode = $state<DesignViewMode>('current');
  let generationError = $state('');
  let saveStatus = $state<SmartDeckSaveStatus>('idle');
  let versionAction = $state<'idle' | 'applying' | 'discarding' | 'regenerating' | 'restoring'>('idle');
  let agentRunState = $state<'idle' | 'thinking' | 'rendering' | 'saving' | 'completed' | 'failed'>('idle');
  let generatedVersionCount = $state(0);
  let codeRequestKey = '';
  let currentCodeRequestKey = '';

  const generationStatus = $derived(
    workspace?.workspace?.status === 'generating'
      ? 'running'
      : workspace?.workspace?.status === 'failed'
        ? 'failed'
        : workspace?.workspace?.status === 'ready' || workspace?.workspace?.status === 'reviewing'
          ? 'ready'
          : 'idle'
  );
  const generatedSlides = $derived(workspace ? workspace.generatedSlides.map(generatedSlideFromBackend) : []);
  const activeSourceSlide = $derived(workspace ? (workspace.sourceSlides.find((slide) => slide.id === activeSourceSlideId) ?? workspace.sourceSlides[0] ?? null) : null);
  const activeDesignVersionId = $derived(
    workspace ? (selectedDesignVersionId ?? workspace.activeDesignVersionId ?? workspace.preferences.activeDesignVersionId ?? null) : null
  );
  const activeDesignVersion = $derived(workspace ? (workspace.designVersions.find((version) => version.id === activeDesignVersionId) ?? null) : null);
  const currentDesignVersion = $derived(workspace ? currentVersionForWorkspace(workspace) : null);
  const previewVersion = $derived(activeDesignVersion ?? null);
  const hasPreviewDesign = $derived(Boolean(previewVersion && previewVersion.id !== currentDesignVersion?.id));
  const currentBackendGeneratedSlide = $derived(generatedSlideForVersion(currentDesignVersion, activeSourceSlideId, null));
  const previewBackendGeneratedSlide = $derived(generatedSlideForVersion(previewVersion, activeSourceSlideId, activeGeneratedSlideId));
  const currentGeneratedSlides = $derived(currentDesignVersion ? currentDesignVersion.generatedSlides.map(generatedSlideFromBackend) : []);
  const previewGeneratedSlides = $derived(previewVersion ? previewVersion.generatedSlides.map(generatedSlideFromBackend) : generatedSlides);
  const selectedCountLabel = $derived(selectedSourceSlideIds.length === 1 ? '1 slide selected' : `${selectedSourceSlideIds.length} slides selected`);

  $effect.pre(() => {
    if (initialized) return;
    workspace = $state.snapshot(initialWorkspace);
    selectedSourceSlideIds = initialSelectedSourceSlideIds(initialWorkspace);
    activeSourceSlideId = initialActiveSourceSlideId(initialWorkspace);
    activeGeneratedSlideId = initialActiveGeneratedSlideId(initialWorkspace);
    selectedDesignVersionId = initialSelectedDesignVersionId(initialWorkspace, initialPreviewDesignVersionId);
    selectedElementId = initialWorkspace.preferences.selectedElementId ?? initialWorkspace.workspace.selectedElementId ?? null;
    initialized = true;

    const requestedPreview = selectedDesignVersionId
      ? initialWorkspace.designVersions.find((version) => version.id === selectedDesignVersionId && version.status !== 'discarded')
      : null;
    const currentVersion = currentVersionForWorkspace(initialWorkspace);
    if (requestedPreview && requestedPreview.id !== currentVersion?.id) {
      activateDesignVersionState(requestedPreview, initialPreviewDesignVersionId ? 'preview' : 'current');
    }
  });

  $effect(() => {
    if (!workspace || !activeGeneratedSlideId) {
      generatedSlideCode = null;
      selectedElementId = null;
      return;
    }

    const requestKey = `${workspace.deck.id}:${activeGeneratedSlideId}`;
    codeRequestKey = requestKey;
    void getGeneratedSlideCode(workspace.deck.id, activeGeneratedSlideId)
      .then((code) => {
        if (codeRequestKey === requestKey) {
          generatedSlideCode = code;
          if (selectedElementId && !code.renderSchema.elements.some((element) => element.id === selectedElementId)) {
            selectedElementId = null;
          }
        }
      })
      .catch((error) => {
        if (codeRequestKey === requestKey) {
          generatedSlideCode = null;
          generationError = error instanceof Error ? error.message : 'Generated slide code could not be loaded.';
        }
      });
  });

  $effect(() => {
    const slideId = currentBackendGeneratedSlide?.id ?? null;
    if (!workspace || !slideId) {
      currentGeneratedSlideCode = null;
      return;
    }

    const requestKey = `${workspace.deck.id}:current:${slideId}`;
    currentCodeRequestKey = requestKey;
    void getGeneratedSlideCode(workspace.deck.id, slideId)
      .then((code) => {
        if (currentCodeRequestKey === requestKey) {
          currentGeneratedSlideCode = code;
        }
      })
      .catch(() => {
        if (currentCodeRequestKey === requestKey) {
          currentGeneratedSlideCode = null;
        }
      });
  });

  function currentVersionForWorkspace(value: SmartDeckWorkspacePayload) {
    return (
      value.designVersions.find((version) => version.isActive && version.status !== 'discarded') ??
      value.designVersions.find((version) => version.status === 'applied' || version.status === 'accepted') ??
      null
    );
  }

  function generatedSlideForVersion(
    version: DesignVersion | null,
    sourceSlideId: string | null,
    preferredGeneratedSlideId: string | null
  ): SmartDeckWorkspacePayload['generatedSlides'][number] | null {
    if (!version) return null;
    if (preferredGeneratedSlideId) {
      const preferred = version.generatedSlides.find((slide) => slide.id === preferredGeneratedSlideId);
      if (preferred) return preferred;
    }
    if (sourceSlideId) {
      const sourceMatch = version.generatedSlides.find((slide) => slide.sourceSlideId === sourceSlideId);
      if (sourceMatch) return sourceMatch;
    }
    return version.generatedSlides[0] ?? null;
  }

  function hydrateWorkspaceState(nextWorkspace: SmartDeckWorkspacePayload, nextMode: DesignViewMode = designViewMode) {
    workspace = nextWorkspace;
    selectedSourceSlideIds = initialSelectedSourceSlideIds(nextWorkspace);
    activeSourceSlideId = initialActiveSourceSlideId(nextWorkspace);
    selectedElementId = nextWorkspace.preferences.selectedElementId ?? nextWorkspace.workspace.selectedElementId ?? null;
    const currentVersion = currentVersionForWorkspace(nextWorkspace);

    if (nextMode === 'current') {
      selectedDesignVersionId = currentVersion?.id ?? null;
      const currentSlide = generatedSlideForVersion(currentVersion, activeSourceSlideId, null);
      activeGeneratedSlideId = currentSlide?.id ?? null;
      selectedElementId = null;
      generatedSlideCode = null;
      return;
    }

    selectedDesignVersionId = initialSelectedDesignVersionId(
      nextWorkspace,
      activeDesignVersionId && activeDesignVersionId !== currentVersion?.id ? activeDesignVersionId : null
    );
    activeGeneratedSlideId = initialActiveGeneratedSlideId(nextWorkspace);
  }

  function activateDesignVersionState(version: DesignVersion, nextMode?: DesignViewMode) {
    if (!workspace) return;
    const matchingSlide = generatedSlideForVersion(version, activeSourceSlideId, activeGeneratedSlideId);
    selectedDesignVersionId = version.id;
    activeGeneratedSlideId = matchingSlide?.id ?? version.generatedSlides[0]?.id ?? null;
    selectedElementId = null;
    generatedSlideCode = null;
    designViewMode = nextMode ?? (currentVersionForWorkspace(workspace)?.id === version.id ? 'current' : 'preview');
    workspace = {
      ...workspace,
      workspace: {
        ...workspace.workspace,
        activeDesignVersionId: version.id,
        activeGeneratedSlideId,
        selectedElementId: null,
        status: version.status === 'discarded' ? workspace.workspace.status : 'reviewing'
      },
      preferences: {
        ...workspace.preferences,
        activeDesignVersionId: version.id,
        activeGeneratedSlideId,
        selectedElementId: null
      },
      activeDesignVersionId: version.id,
      activeGeneratedSlideId,
      generatedSlides: version.generatedSlides
    };
  }

  function updatePreviewDesignVersionQuery(versionId: string | null) {
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    if (versionId) {
      url.searchParams.set('previewDesignVersionId', versionId);
    } else {
      url.searchParams.delete('previewDesignVersionId');
    }
    window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`);
  }

  async function refreshSmartDeckWorkspace(nextMode: DesignViewMode = designViewMode) {
    if (!workspace) return;
    const nextWorkspace = await getSmartDeckWorkspace(workspace.deck.id);
    hydrateWorkspaceState(nextWorkspace, nextMode);
  }

  function persistPreferences(next: {
    selectedSourceSlideIds?: string[];
    activeSourceSlideId?: string | null;
    activeGeneratedSlideId?: string | null;
  }) {
    if (!workspace) return;
    void patchSmartDeckPreferences(workspace.deck.id, next).catch((error) => {
      generationError = error instanceof Error ? error.message : 'Smart Deck preferences could not be saved.';
    });
  }

  async function persistTopicPreferences(context: {
    audience: string | null;
    deckType: SmartDeckDeckType;
    preferredModel: string | null;
    selectedSubject: SmartDeckSubject;
    selectedActionId: string | null;
  }) {
    if (!workspace) return;
    try {
      await patchSmartDeckPreferences(workspace.deck.id, {
        audience: context.audience,
        deckType: context.deckType,
        preferredModel: context.preferredModel,
        selectedSubject: context.selectedSubject,
        selectedActionId: context.selectedActionId
      });
      workspace = {
        ...workspace,
        preferences: {
          ...workspace.preferences,
          audience: context.audience,
          deckType: context.deckType,
          preferredModel: context.preferredModel,
          selectedSubject: context.selectedSubject,
          selectedActionId: context.selectedActionId
        }
      };
    } catch (error) {
      generationError = error instanceof Error ? error.message : 'Smart Deck topic preferences could not be saved.';
    }
  }

  function toggleSlide(slideId: string) {
    agentRunState = 'idle';
    selectedSourceSlideIds = selectedSourceSlideIds.includes(slideId)
      ? selectedSourceSlideIds.filter((id) => id !== slideId)
      : [...selectedSourceSlideIds, slideId];
    persistPreferences({ selectedSourceSlideIds });
  }

  function setActiveSlide(slideId: string) {
    agentRunState = 'idle';
    activeSourceSlideId = slideId;
    persistPreferences({ activeSourceSlideId: slideId });
  }

  function selectAllSlides() {
    if (!workspace) return;
    agentRunState = 'idle';
    selectedSourceSlideIds = workspace.sourceSlides.map((slide) => slide.id);
    persistPreferences({ selectedSourceSlideIds });
  }

  function clearSlideSelection() {
    agentRunState = 'idle';
    selectedSourceSlideIds = [];
    persistPreferences({ selectedSourceSlideIds });
  }

  function selectGeneratedSlide(slideId: string) {
    if (!workspace) return;
    agentRunState = 'idle';
    designViewMode = designViewMode === 'current' ? 'preview' : designViewMode;
    activeGeneratedSlideId = slideId;
    selectedElementId = null;
    void updateSmartDeckSelection(workspace.deck.id,
    {
      activeGeneratedSlideId: slideId,
      selectedElementId: null
    }).catch((error) => {
      generationError = error instanceof Error ? error.message : 'Smart Deck selection could not be saved.';
    });
  }

  function selectElement(elementId: string) {
    if (!workspace) return;
    agentRunState = 'idle';
    selectedElementId = elementId;
    void updateSmartDeckSelection(workspace.deck.id, {
      activeGeneratedSlideId,
      selectedElementId: elementId
    }).catch((error) => {
      generationError = error instanceof Error ? error.message : 'Smart Deck selected element could not be saved.';
    });
  }

  async function sendPrompt(input: SmartDeckGenerationInput) {
    if (!workspace) return;
    const effectiveSelectedSourceSlideIds = input.selectedSourceSlideIds.length > 0 ? input.selectedSourceSlideIds : selectedSourceSlideIds;
    if (effectiveSelectedSourceSlideIds.length === 0) {
      generationError = 'Select at least one source slide before generating.';
      return;
    }

    generationError = '';
    agentRunState = 'thinking';
    generatedVersionCount = 0;
    if (selectedElementId && activeGeneratedSlideId) {
      try {
        workspace = {
          ...workspace,
          workspace: {
            ...workspace.workspace,
            status: 'generating'
          }
        };
        const variation = await createElementVariationJob(workspace.deck.id, activeGeneratedSlideId, selectedElementId, {
          instruction: input.userPrompt ?? input.prompt,
          variationCount: 1
        });
        if (variation.workspace) {
          hydrateWorkspaceState(variation.workspace, 'preview');
        } else {
          await refreshSmartDeckWorkspace('preview');
        }
        if (variation.designVersion) {
          activateDesignVersionState(variation.designVersion, 'preview');
          updatePreviewDesignVersionQuery(variation.designVersion.id);
        } else {
          activeGeneratedSlideId = variation.generatedSlide?.id ?? variation.variationJob.generatedSlideId ?? activeGeneratedSlideId;
        }
        selectedElementId = variation.element.id;
        generatedSlideCode = activeGeneratedSlideId ? await getGeneratedSlideCode(workspace.deck.id, activeGeneratedSlideId) : null;
        designViewMode = 'preview';
        generatedVersionCount = 1;
        agentRunState = 'completed';
        return;
      } catch (error) {
        generationError = error instanceof Error ? error.message : 'Smart Deck element variation failed.';
        agentRunState = 'failed';
        workspace = {
          ...workspace,
          workspace: {
            ...workspace.workspace,
            status: 'failed'
          }
        };
        return;
      }
    }

    workspace = {
      ...workspace,
      workspace: {
        ...workspace.workspace,
        status: 'generating'
      }
    };

    try {
      const response = await startSmartDeckGenerationWorkflow(workspace.deck.id, {
        ...input,
        prompt: input.prompt,
        selectedSourceSlideIds: effectiveSelectedSourceSlideIds,
        activeSourceSlideId: input.activeSourceSlideId ?? activeSourceSlideId,
        selectedElementId: input.selectedElementId ?? selectedElementId
      });
      if (response.workspace) {
        workspace = response.workspace;
        selectedSourceSlideIds = response.workspace.preferences.selectedSourceSlideIds;
        activeSourceSlideId = response.workspace.activeSourceSlideId ?? activeSourceSlideId;
      }
      agentRunState = response.status === 'failed' ? 'failed' : 'rendering';
      const finalRun = await waitForWorkflowJobCompletion(response.runId, 'Smart Deck generation failed.');
      if (finalRun.status !== 'completed' || !finalRun.designVersion || !finalRun.workspace) {
        generationError = finalRun.errorMessage ?? 'Smart Deck generation failed.';
        agentRunState = 'failed';
        if (finalRun.workspace) {
          workspace = finalRun.workspace;
        }
        return;
      }
      workspace = finalRun.workspace;
      selectedSourceSlideIds = finalRun.workspace.preferences.selectedSourceSlideIds;
      activeSourceSlideId = finalRun.workspace.activeSourceSlideId ?? activeSourceSlideId;
      activateDesignVersionState(finalRun.designVersion, 'preview');
      updatePreviewDesignVersionQuery(finalRun.designVersion.id);
      generatedVersionCount = finalRun.designVersion.generatedSlides.length;
      designViewMode = 'preview';
      agentRunState = 'completed';
    } catch (error) {
      generationError = error instanceof Error ? error.message : 'Smart Deck generation failed.';
      agentRunState = 'failed';
      workspace = {
        ...workspace,
        workspace: {
          ...workspace.workspace,
          status: 'failed'
        }
      };
    }
  }

  function reviewChanges() {
    if (!workspace) return;
    void goto(`/decks/${workspace.deck.id}/batches`);
  }

  async function previewDesignVersion(version: DesignVersion) {
    if (!workspace) return;
    agentRunState = 'idle';
    activateDesignVersionState(version, currentDesignVersion?.id === version.id ? 'current' : 'preview');
    updatePreviewDesignVersionQuery(currentDesignVersion?.id === version.id ? null : version.id);
    try {
      await patchSmartDeckPreferences(workspace.deck.id, {
        activeDesignVersionId: version.id,
        activeGeneratedSlideId,
        selectedElementId: null
      });
    } catch (error) {
      generationError = error instanceof Error ? error.message : 'Design version preview could not be saved.';
    }
  }

  async function discardActiveDesignVersion(versionId: string) {
    if (!workspace) return;
    saveStatus = 'saving';
    versionAction = 'discarding';
    try {
      await discardDesignVersion(workspace.deck.id, versionId);
      designViewMode = 'current';
      updatePreviewDesignVersionQuery(null);
      await refreshSmartDeckWorkspace('current');
      saveStatus = 'idle';
    } catch (error) {
      saveStatus = 'failed';
      generationError = error instanceof Error ? error.message : 'Design version could not be discarded.';
    } finally {
      versionAction = 'idle';
    }
  }

  async function restoreActiveDesignVersion(versionId: string) {
    if (!workspace) return;
    saveStatus = 'saving';
    versionAction = 'restoring';
    try {
      await restoreDesignVersion(workspace.deck.id, versionId);
      designViewMode = 'current';
      updatePreviewDesignVersionQuery(null);
      await refreshSmartDeckWorkspace('current');
      saveStatus = 'saved';
    } catch (error) {
      saveStatus = 'failed';
      generationError = error instanceof Error ? error.message : 'Design version could not be restored.';
    } finally {
      versionAction = 'idle';
    }
  }

  async function applyActiveDesignVersion(versionId = activeDesignVersionId) {
    if (!workspace) return;
    if (!versionId) return;

    saveStatus = 'saving';
    versionAction = 'applying';
    try {
      await applyDesignVersion(workspace.deck.id, versionId);
      designViewMode = 'current';
      updatePreviewDesignVersionQuery(null);
      await refreshSmartDeckWorkspace('current');
      saveStatus = 'saved';
    } catch (error) {
      saveStatus = 'failed';
      generationError = error instanceof Error ? error.message : 'Design version could not be applied.';
    } finally {
      versionAction = 'idle';
    }
  }

  function showCurrentDesign() {
    designViewMode = 'current';
    updatePreviewDesignVersionQuery(null);
    if (currentBackendGeneratedSlide) {
      activeGeneratedSlideId = currentBackendGeneratedSlide.id;
    }
  }

  function showPreviewDesign() {
    if (!hasPreviewDesign && !previewBackendGeneratedSlide) return;
    designViewMode = 'preview';
    if (activeDesignVersionId && activeDesignVersionId !== currentDesignVersion?.id) {
      updatePreviewDesignVersionQuery(activeDesignVersionId);
    }
    if (previewBackendGeneratedSlide) {
      activeGeneratedSlideId = previewBackendGeneratedSlide.id;
    }
  }

  function showCompareDesign() {
    if (!hasPreviewDesign) return;
    designViewMode = 'compare';
  }

  async function compareDesignVersion(versionId: string) {
    if (!workspace) return;
    const version = workspace.designVersions.find((item) => item.id === versionId);
    if (!version) return;
    if (activeDesignVersionId !== versionId) {
      await previewDesignVersion(version);
    }
    if (version.id !== currentDesignVersion?.id) {
      designViewMode = 'compare';
    }
  }

  async function regenerateDesignVersion(versionId: string) {
    if (!workspace) return;
    const version = workspace.designVersions.find((item) => item.id === versionId);
    if (!version) return;

    const versionSourceSlideIds = Array.from(
      new Set(version.generatedSlides.map((slide) => slide.sourceSlideId).filter((id): id is string => Boolean(id)))
    );
    const nextSelectedSourceSlideIds = versionSourceSlideIds.length > 0 ? versionSourceSlideIds : selectedSourceSlideIds;
    if (nextSelectedSourceSlideIds.length === 0) {
      generationError = 'Select source slides before regenerating this design.';
      return;
    }

    const nextActiveSourceSlideId =
      version.generatedSlides.find((slide) => slide.sourceSlideId)?.sourceSlideId ?? activeSourceSlideId ?? nextSelectedSourceSlideIds[0] ?? null;

    versionAction = 'regenerating';
    selectedSourceSlideIds = nextSelectedSourceSlideIds;
    activeSourceSlideId = nextActiveSourceSlideId;
    selectedElementId = null;

    await sendPrompt({
      prompt: `Create a fresh version of this design direction. Keep the same goal, improve the visual result, and preserve the selected slide context.${version.summary ? ` Previous direction: ${version.summary}` : ''}`,
      selectedSourceSlideIds: nextSelectedSourceSlideIds,
      activeSourceSlideId: nextActiveSourceSlideId,
      selectedElementId: null,
      audience: workspace.preferences.audience ?? workspace.deck.audience ?? null,
      deckType: workspace.preferences.deckType ?? undefined,
      preferredModel: workspace.preferences.preferredModel ?? null,
      selectedSubject: workspace.preferences.selectedSubject ?? null,
      actionId: workspace.preferences.selectedActionId ?? null,
      userPrompt: 'Regenerate selected design version',
      latestBatchId: version.id
    });
    versionAction = 'idle';
  }
</script>

{#if workspace}
<section class="smart-deck-workspace">
  {#if generationError}
    <div class="workspace-error" role="alert">{generationError}</div>
  {/if}

  <div class="workspace-grid">
    <PdfSlideMiniaturesCard
      sourcePdfSlides={workspace.sourceSlides}
      {selectedSourceSlideIds}
      {activeSourceSlideId}
      onToggleSlide={toggleSlide}
      onSetActiveSlide={setActiveSlide}
      onSelectAll={selectAllSlides}
      onClearSelection={clearSlideSelection}
    />

    <div class="workspace-main-stack">
      <DeckDesignShellCard
        activeBatchId={activeDesignVersionId}
        generatedSlides={generatedSlides}
        {currentGeneratedSlides}
        {previewGeneratedSlides}
        {activeGeneratedSlideId}
        currentGeneratedSlideId={currentBackendGeneratedSlide?.id ?? null}
        previewGeneratedSlideId={previewBackendGeneratedSlide?.id ?? activeGeneratedSlideId}
        activeSourceSlide={activeSourceSlide}
        {generationStatus}
        {generatedSlideCode}
        {currentGeneratedSlideCode}
        previewGeneratedSlideCode={generatedSlideCode}
        currentRenderSchema={currentGeneratedSlideCode?.renderSchema ?? null}
        previewRenderSchema={generatedSlideCode?.renderSchema ?? null}
        activeRenderSchema={designViewMode === 'current' ? currentGeneratedSlideCode?.renderSchema ?? null : generatedSlideCode?.renderSchema ?? null}
        {designViewMode}
        {hasPreviewDesign}
        {selectedElementId}
        selectedGeneratedElementId={selectedElementId}
        onSelectGeneratedSlide={selectGeneratedSlide}
        onSelectElement={selectElement}
        onShowCurrent={showCurrentDesign}
        onShowPreview={showPreviewDesign}
        onShowCompare={showCompareDesign}
      />

      <section class="selection-status-bar" aria-label="Selected source slides">
        <div>
          <strong>{selectedCountLabel}</strong>
          <span>{selectedSourceSlideIds.length > 0 ? 'Included in the next redesign.' : 'Select source slides to generate a version.'}</span>
        </div>
        <button type="button" disabled={selectedSourceSlideIds.length === 0} onclick={clearSlideSelection}>Clear selection</button>
      </section>
    </div>

    <div class="right-stack">
      <LlmChatCard
        chatMessages={workspace.messages}
        {selectedSourceSlideIds}
        selectedSlides={workspace.sourceSlides.filter((slide) => selectedSourceSlideIds.includes(slide.id))}
        deckAudience={workspace.deck.audience}
        deckPurpose={workspace.deck.purpose}
        preferredAudience={workspace.preferences.audience ?? workspace.deck.audience ?? null}
        preferredDeckType={workspace.preferences.deckType ?? null}
        preferredModel={workspace.preferences.preferredModel ?? null}
        preferredSelectedSubject={workspace.preferences.selectedSubject ?? null}
        preferredSelectedActionId={workspace.preferences.selectedActionId ?? null}
        {selectedElementId}
        {generationStatus}
        activeBatchId={activeDesignVersionId}
        previewMode={hasPreviewDesign}
        {agentRunState}
        {generatedVersionCount}
        onSendMessage={sendPrompt}
        onContextChange={persistTopicPreferences}
        onReviewChanges={reviewChanges}
        onApplyAll={applyActiveDesignVersion}
      />

      <GeneratedBatchSaveCard
        activeDesignVersionId={activeDesignVersionId}
        currentDesignVersionId={currentDesignVersion?.id ?? null}
        activeVersion={activeDesignVersion}
        designVersions={workspace.designVersions}
        {designViewMode}
        {saveStatus}
        applying={versionAction === 'applying'}
        discarding={versionAction === 'discarding'}
        regenerating={versionAction === 'regenerating'}
        restoring={versionAction === 'restoring'}
        onPreviewDesignVersion={previewDesignVersion}
        onApplyDesignVersion={applyActiveDesignVersion}
        onDiscardDesignVersion={discardActiveDesignVersion}
        onRestoreDesignVersion={restoreActiveDesignVersion}
        onCompareDesignVersion={compareDesignVersion}
        onShowCurrent={showCurrentDesign}
        onRegenerateDesignVersion={regenerateDesignVersion}
      />
    </div>
  </div>
</section>
{/if}

<style>
  .smart-deck-workspace {
    --smart-deck-slide-rail-width: clamp(13.5rem, 17vw, 17rem);
    --smart-deck-right-panel-width: clamp(20rem, 25vw, 24rem);
    display: grid;
    gap: var(--workspace-gap);
    height: calc(100vh - var(--topbar-height) - 1.25rem);
    min-height: 42rem;
    overflow: hidden;
  }

  .workspace-grid {
    display: grid;
    grid-template-columns: var(--smart-deck-slide-rail-width) minmax(0, 1fr) var(--smart-deck-right-panel-width);
    gap: var(--workspace-gap);
    align-items: stretch;
    min-height: 0;
  }

  .workspace-main-stack,
  .right-stack {
    display: grid;
    gap: var(--workspace-gap);
    min-height: 0;
  }

  .workspace-main-stack {
    grid-template-rows: minmax(0, 1fr) auto;
  }

  .right-stack {
    grid-template-rows: minmax(0, 1fr) auto;
  }

  .workspace-error {
    border: 1px solid var(--danger);
    border-radius: 8px;
    background: var(--surface);
    color: var(--danger);
    padding: 0.8rem 0.95rem;
  }

  .selection-status-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    min-height: 4.75rem;
    border: 1px solid var(--line-strong);
    border-radius: var(--radius-md);
    background: var(--surface);
    padding: 0.9rem 1rem;
    box-shadow: var(--shadow);
  }

  .selection-status-bar div {
    display: grid;
    gap: 0.2rem;
    min-width: 0;
  }

  .selection-status-bar span {
    color: var(--muted);
  }

  .selection-status-bar button {
    border: 0;
    background: transparent;
    color: var(--accent);
    white-space: nowrap;
  }

  .selection-status-bar button:disabled {
    color: var(--muted);
    cursor: not-allowed;
  }

  @media (max-width: 1180px) {
    .smart-deck-workspace {
      height: auto;
      overflow: visible;
    }

    .workspace-grid {
      grid-template-columns: 1fr;
    }

    .right-stack {
      grid-template-rows: auto;
    }
  }
</style>
