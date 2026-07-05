<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import { deckProductApiPath } from '$lib/contracts';
  import type {
    DeckWorkspaceModel,
    DeckShellProperties,
    DeckWorkspacePreferences,
    DesignBatchPreview,
    SaveConfirmation,
    UpdateDeckShellPropertiesRequest,
    SubmitSlideFeedbackRequest,
    UpdateDeckWorkspacePreferencesRequest
  } from '@deck-aistack-codes/shared';
  import DeckLeftPanel from '$components/deck-shell/DeckLeftPanel.svelte';
  import DeckAiChatPopup from '$components/deck-shell/DeckAiChatPopup.svelte';
  import DeckRightInspector from '$components/deck-shell/DeckRightInspector.svelte';
  import SmartDeckPropertiesDrawer from '$components/SmartDeckPropertiesDrawer.svelte';
  import DeckAiPanel from '$components/deck-shell/DeckAiPanel.svelte';
  import DeckBottomBar from '$components/deck-shell/DeckBottomBar.svelte';
  import DeckCanvas from '$components/deck-shell/DeckCanvas.svelte';
  import DeckToolRail from '$components/deck-shell/DeckToolRail.svelte';
  import DeckShellTopBar from '$components/deck-shell/DeckShellTopBar.svelte';
  import SaveConfirmationBanner from '$lib/components/deckService/feedback/SaveConfirmationBanner.svelte';
  import { waitForWorkflowJobCompletion } from '$lib/api/deckService/workflow.client';
  import type { SaveConfirmationBannerModel } from '$lib/contracts/types';
  import type { AiDesignCommand, AiDesignPreset } from '$lib/types/ai-design';
  import { normalizeSaveConfirmation, toSaveConfirmationBannerModel } from '$lib/utils/saveConfirmation';
  import type { BlockClassification, DeckGraph } from '$types/domain';

  interface PreparedIteration {
    scopeLabel: string;
    prompt: string;
    selectedSlides: string[];
    actionCount: number;
  }

  interface Props {
    graph: DeckGraph;
    workspaceModel: DeckWorkspaceModel;
    properties?: DeckShellProperties;
    workspacePreferences?: DeckWorkspacePreferences;
    selectedSlideId?: string;
    latestBatches?: DesignBatchPreview[];
    initialShellConfirmation?: SaveConfirmation | null;
    workspaceHrefBase?: string;
    readOnlyMode?: boolean;
    backHref?: string;
    backLabel?: string;
  }

  let {
    graph,
    workspaceModel,
    properties,
    workspacePreferences,
    selectedSlideId,
    latestBatches = [],
    initialShellConfirmation = null,
    workspaceHrefBase = `/decks/${graph.deck.id}/smart-deck`,
    readOnlyMode = false,
    backHref = '/dashboard',
    backLabel = 'Dashboard'
  }: Props = $props();

  // The shell keeps a small local interaction state, but every durable user action now goes through typed API routes.
  let selectedSlideIds = $state<string[]>([]);
  let hasInitializedSlideSelection = $state(false);
  let mode = $state<'play' | 'edit' | 'preview'>('edit');
  let scope = $state<'selected_slides' | 'whole_deck'>('whole_deck');
  let instruction = $state('Create a cleaner investor-ready iteration and tighten the narrative on the selected slides.');
  let preparedIteration = $state<PreparedIteration | null>(null);
  let propertiesOpen = $state(false);
  let propertiesState = $state<DeckShellProperties | undefined>();
  let workspaceState = $state<DeckWorkspacePreferences | undefined>();
  let activeTool = $state<DeckWorkspacePreferences['activeTool']>('slides');
  let leftPanelOpen = $state(true);
  let selectedBlockId = $state<string | undefined>();
  let saveMessage = $state<SaveConfirmationBannerModel | null>(null);
  let blockSaveMessage = $state<SaveConfirmationBannerModel | null>(null);
  let shellConfirmation = $state<SaveConfirmationBannerModel | null>(null);
  let hasAppliedInitialShellConfirmation = $state(false);
  let shellError = $state<string | null>(null);
  let isSavingProperties = $state(false);
  let isSavingBlock = $state(false);
  let isCreatingIteration = $state(false);
  let isSubmittingVersionFeedback = $state(false);
  let isAddingSlide = $state(false);
  let chatOpen = $state(false);
  let chatTarget = $state<'current_slide' | 'selected_slides' | 'whole_deck'>('whole_deck');
  let chatInstruction = $state('Create a premium investor-facing design version and sharpen the story flow.');
  let chatPreset = $state<AiDesignPreset | null>('investor_ready');
  let workspaceModelState = $state<DeckWorkspaceModel>({
    deck: {
      id: '',
      workspaceId: '',
      title: '',
      audience: '',
      purpose: '',
      status: 'draft',
      summary: '',
      createdAt: '',
      updatedAt: '',
      generationStatus: 'idle',
      generationMode: 'mock',
      latestGenerationRunId: null
    },
    slides: [],
    versions: [],
    feedback: []
  });
  let generationMessage = $state<string | null>(null);

  function buildSuccessConfirmation(title: string, message?: string): SaveConfirmationBannerModel {
    return {
      title,
      message: message ?? null,
      tone: 'success'
    };
  }

  const selectedSlide = $derived(graph.slides.find((slide) => slide.id === selectedSlideId) ?? graph.slides[0]);
  const selectedBlocks = $derived(graph.blocks.filter((block) => block.slideId === selectedSlide?.id));
  const classificationLookup = $derived(
    graph.classifications.reduce<Record<string, BlockClassification | undefined>>((lookup, classification) => {
      lookup[classification.blockId] = classification;
      return lookup;
    }, {})
  );
  const selectedBlock = $derived(selectedBlocks.find((block) => block.id === selectedBlockId) ?? selectedBlocks[0]);
  const selectedBlockClassification = $derived(selectedBlock ? classificationLookup[selectedBlock.id] : undefined);
  const selectedFindings = $derived(graph.findings.filter((finding) => finding.slideId === selectedSlide?.id));
  const selectedSuggestions = $derived(graph.suggestions.filter((suggestion) => suggestion.slideId === selectedSlide?.id));
  const selectedBlockFindings = $derived(
    selectedBlock ? selectedFindings.filter((finding) => !finding.blockId || finding.blockId === selectedBlock.id) : []
  );
  const selectedBlockSuggestions = $derived(
    selectedBlock ? selectedSuggestions.filter((suggestion) => !suggestion.blockId || suggestion.blockId === selectedBlock.id) : []
  );
  const selectedSlides = $derived(graph.slides.filter((slide) => selectedSlideIds.includes(slide.id)));
  const canPrepareIteration = $derived(scope === 'whole_deck' || selectedSlideIds.length > 0);
  const latestBatch = $derived(latestBatches[0] ?? null);
  const selectedGeneratedVersions = $derived(
    [...workspaceModelState.versions]
      .filter((version) => version.sourceSlideId === selectedSlide?.id)
      .sort((left, right) => right.versionNumber - left.versionNumber)
  );
  const recommendationCounts = $derived(
    graph.suggestions.reduce<Record<string, number>>((lookup, suggestion) => {
      lookup[suggestion.slideId] = (lookup[suggestion.slideId] ?? 0) + 1;
      return lookup;
    }, {})
  );
  const findingSeverities = $derived(
    graph.findings.reduce<Record<string, string | undefined>>((lookup, finding) => {
      if (!lookup[finding.slideId]) {
        lookup[finding.slideId] = finding.severity;
      }

      return lookup;
    }, {})
  );

  function readOnlyModeMessage(action: string) {
    return `${action} is disabled. This workflow requires a connected Deck AIStack service.`;
  }

  $effect(() => {
    if (!hasInitializedSlideSelection && graph.slides.length > 0) {
      selectedSlideIds = graph.slides.map((slide) => slide.id);
      hasInitializedSlideSelection = true;
    }
  });

  $effect(() => {
    blockSaveMessage = null;

    if (selectedBlocks.length === 0) {
      selectedBlockId = undefined;
      return;
    }

    // Keep one block selected per slide so the inspector always has a concrete editing target.
    if (!selectedBlocks.some((block) => block.id === selectedBlockId)) {
      selectedBlockId = selectedBlocks[0]?.id;
    }
  });

  $effect(() => {
    propertiesState = properties;
  });

  $effect(() => {
    workspaceState = workspacePreferences;
    activeTool = workspacePreferences?.activeTool ?? 'slides';
    leftPanelOpen = workspacePreferences?.leftPanelOpen ?? true;
    chatOpen = workspacePreferences?.chatOpen ?? false;
  });

  $effect(() => {
    workspaceModelState = workspaceModel;
  });

  $effect(() => {
    const initialConfirmation = toSaveConfirmationBannerModel(initialShellConfirmation);
    if (!hasAppliedInitialShellConfirmation || initialConfirmation) {
      shellConfirmation = initialConfirmation;
      hasAppliedInitialShellConfirmation = true;
    }
  });

  function toggleSlideSelection(slideId: string) {
    const nextSelection = selectedSlideIds.includes(slideId)
      ? selectedSlideIds.filter((id) => id !== slideId)
      : [...selectedSlideIds, slideId];

    selectedSlideIds = nextSelection;
    scope = nextSelection.length === graph.slides.length ? 'whole_deck' : 'selected_slides';
  }

  function selectAllSlides() {
    selectedSlideIds = graph.slides.map((slide) => slide.id);
    scope = 'whole_deck';
  }

  function clearSelectedSlides() {
    selectedSlideIds = [];
    scope = 'selected_slides';
  }

  // The iteration stays reviewable by design; this stages the next version request without mutating the deck.
  function prepareIteration() {
    if (!canPrepareIteration) return;

    const iterationSlides = scope === 'whole_deck' ? graph.slides : selectedSlides;
    const actionCount =
      iterationSlides.reduce((total, slide) => total + graph.findings.filter((finding) => finding.slideId === slide.id).length, 0) +
      iterationSlides.reduce((total, slide) => total + graph.suggestions.filter((suggestion) => suggestion.slideId === slide.id).length, 0);

    preparedIteration = {
      scopeLabel: scope === 'whole_deck' ? 'Whole deck' : `${iterationSlides.length} selected slides`,
      prompt: instruction.trim() || 'Create an investor-ready iteration using the current deck context.',
      selectedSlides: iterationSlides.map((slide) => slide.title),
      actionCount
    };
  }

  function openSmartEdit() {
    if (!selectedSlide) return;
    if (readOnlyMode) {
      shellError = readOnlyModeMessage('Smart Edit');
      return;
    }
    void goto(`/decks/${graph.deck.id}/smart-edit?slide=${selectedSlide.id}`);
  }

  function openBatches() {
    if (readOnlyMode) {
      shellError = readOnlyModeMessage('Version generation');
      return;
    }

    const params = new URLSearchParams();

    if (scope === 'selected_slides' && selectedSlideIds.length > 0) {
      params.set('slides', selectedSlideIds.join(','));
    }

    if (preparedIteration?.prompt) {
      params.set('brief', preparedIteration.prompt);
    }

    void goto(`/decks/${graph.deck.id}/batches${params.size > 0 ? `?${params.toString()}` : ''}`);
  }

  function openChanges() {
    if (readOnlyMode) {
      shellError = readOnlyModeMessage('Due diligence');
      return;
    }

    void goto(`/decks/${graph.deck.id}/due-diligence`);
  }

  function selectBlock(blockId: string) {
    selectedBlockId = blockId;
  }

  async function persistProperties(nextProperties: UpdateDeckShellPropertiesRequest) {
    if (readOnlyMode) {
      shellError = readOnlyModeMessage('Property editing');
      return;
    }

    isSavingProperties = true;
    shellError = null;
    saveMessage = null;

    try {
      const response = await fetch(`/api/decks/${graph.deck.id}/properties`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(nextProperties)
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const payload = (await response.json()) as {
        properties?: DeckShellProperties;
        confirmation?: Record<string, unknown> | null;
      };
      if (payload.properties) {
        propertiesState = payload.properties;
        const nextConfirmation =
          toSaveConfirmationBannerModel(normalizeSaveConfirmation(payload.confirmation, 'deck_properties_saved')) ??
          buildSuccessConfirmation('Deck saved successfully', 'Your deck properties are secure and ready for the next step.');
        saveMessage = nextConfirmation;
        shellConfirmation = nextConfirmation;
      }
    } catch (error) {
      shellError = error instanceof Error ? error.message : 'Could not save deck properties.';
    } finally {
      isSavingProperties = false;
    }
  }

  async function addSlide() {
    if (readOnlyMode) {
      shellError = readOnlyModeMessage('Slide creation');
      return;
    }

    isAddingSlide = true;
    shellError = null;

    try {
      const response = await fetch(`/api/decks/${graph.deck.id}/slides`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const payload = (await response.json()) as { slide?: { id?: string } };
      const newSlideId = payload.slide?.id;

      await invalidateAll();
      if (newSlideId) {
        await goto(`${workspaceHrefBase}?slide=${newSlideId}`);
      }
    } catch (error) {
      shellError = error instanceof Error ? error.message : 'Could not create a new slide.';
    } finally {
      isAddingSlide = false;
    }
  }

  async function saveSelectedBlock(nextText: string) {
    if (!selectedBlock) return;
    if (readOnlyMode) {
      shellError = readOnlyModeMessage('Block editing');
      return;
    }

    isSavingBlock = true;
    shellError = null;
    blockSaveMessage = null;

    try {
      const response = await fetch(`/api/decks/${graph.deck.id}/blocks/${selectedBlock.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: nextText,
          normalizedText: nextText
        })
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const payload = (await response.json()) as {
        block?: { id?: string };
        confirmation?: Record<string, unknown> | null;
      };
      const nextConfirmation =
        toSaveConfirmationBannerModel(normalizeSaveConfirmation(payload.confirmation, 'deck_block_saved')) ??
        buildSuccessConfirmation('Block saved successfully', 'Your latest content update is now part of this Smart Deck.');
      blockSaveMessage = nextConfirmation;
      shellConfirmation = nextConfirmation;
      await invalidateAll();
    } catch (error) {
      shellError = error instanceof Error ? error.message : 'Could not save the selected block.';
    } finally {
      isSavingBlock = false;
    }
  }

  async function persistWorkspacePreferences(nextWorkspace: UpdateDeckWorkspacePreferencesRequest) {
    if (readOnlyMode) {
      return;
    }

    try {
      const response = await fetch(`/api/decks/${graph.deck.id}/workspace`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(nextWorkspace)
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const payload = (await response.json()) as { workspace?: DeckWorkspacePreferences };
      if (payload.workspace) {
        workspaceState = payload.workspace;
        activeTool = payload.workspace.activeTool;
        leftPanelOpen = payload.workspace.leftPanelOpen;
      }
    } catch (error) {
      shellError = error instanceof Error ? error.message : 'Could not save shell workspace preferences.';
    }
  }

  function changeActiveTool(nextTool: DeckWorkspacePreferences['activeTool']) {
    activeTool = nextTool;
    leftPanelOpen = true;
    shellError = null;
    void persistWorkspacePreferences({
      activeTool: nextTool,
      leftPanelOpen: true
    });
  }

  function toggleLeftPanel() {
    const nextLeftPanelOpen = !leftPanelOpen;
    leftPanelOpen = nextLeftPanelOpen;
    shellError = null;
    void persistWorkspacePreferences({
      activeTool,
      leftPanelOpen: nextLeftPanelOpen
    });
  }

  function persistSelectedSlide(nextSlideId: string) {
    shellError = null;
    void persistWorkspacePreferences({
      selectedSlideId: nextSlideId
    });
  }

  function toggleChatPopup(nextOpen: boolean) {
    chatOpen = nextOpen;
    shellError = null;
    void persistWorkspacePreferences({
      chatOpen: nextOpen
    });
  }

  async function createDesignVersionRequest(options: {
    prompt: string;
    slideIds: string[];
  }) {
    if (readOnlyMode) {
      throw new Error(readOnlyModeMessage('AI generation'));
    }

    const response = await fetch(deckProductApiPath(`/decks/${graph.deck.id}/workflows/smart-deck-generation`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        deckId: graph.deck.id,
        scope: 'selected_slides',
        selectedSlideIds: options.slideIds,
        instruction: options.prompt,
        intentType: 'redesign_slides',
        outputMode: 'editable_slide_versions',
        audience: propertiesState?.audienceLabel ?? graph.deck.audience,
        purpose: propertiesState?.primaryGoal ?? graph.deck.purpose,
        userPrompt: options.prompt,
        latestBatchId: latestBatch?.id ?? null
      })
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }

    const result = (await response.json()) as { runId?: string; run_id?: string };
    const runId = result.runId ?? result.run_id;
    if (!runId) {
      throw new Error('The backend did not return a workflow job id.');
    }

    await waitForWorkflowJobCompletion(runId, 'Smart Deck generation failed.');

    const workspaceResponse = await fetch(deckProductApiPath(`/decks/${graph.deck.id}/workspace`));
    if (!workspaceResponse.ok) {
      throw new Error('The backend did not return a workspace generation payload.');
    }

    const workspacePayload = (await workspaceResponse.json()) as { workspace?: DeckWorkspaceModel };
    if (!workspacePayload.workspace) {
      throw new Error('The backend did not return a workspace generation payload.');
    }

    workspaceModelState = workspacePayload.workspace;
    generationMessage = `Generated ${workspacePayload.workspace.versions.length} reviewable versions in the workspace.`;
    preparedIteration = null;
  }

  async function createVersionFromChat(command: AiDesignCommand) {
    if (!command.command.trim()) return;

    let slideIds: string[] = selectedSlideIds;
    let scopeType: 'selected_slides' | 'whole_deck' = 'selected_slides';

    if (command.scope === 'whole_deck') {
      slideIds = graph.slides.map((slide) => slide.id);
      scopeType = 'whole_deck';
    } else if (command.scope === 'current_slide') {
      slideIds = selectedSlide ? [selectedSlide.id] : [];
      scopeType = 'selected_slides';
    }

    if (slideIds.length === 0 && scopeType === 'selected_slides') {
      shellError = 'Select at least one slide before creating a design version.';
      return;
    }

    isCreatingIteration = true;
    shellError = null;

    try {
      await createDesignVersionRequest({
        prompt: command.command.trim(),
        slideIds
      });
      toggleChatPopup(false);
    } catch (error) {
      shellError = error instanceof Error ? error.message : 'Could not create a design version.';
    } finally {
      isCreatingIteration = false;
    }
  }

  async function createIteration() {
    if (!preparedIteration) return;

    isCreatingIteration = true;
    shellError = null;

    try {
      await createDesignVersionRequest({
        prompt: preparedIteration.prompt,
        slideIds: scope === 'whole_deck' ? graph.slides.map((slide) => slide.id) : selectedSlideIds
      });
    } catch (error) {
      shellError = error instanceof Error ? error.message : 'Could not create a design version.';
    } finally {
      isCreatingIteration = false;
    }
  }

  async function submitGeneratedVersionFeedback(
    versionId: string,
    sourceSlideId: string | null,
    eventType: SubmitSlideFeedbackRequest['eventType'],
    applyToWorkspace: boolean
  ) {
    if (readOnlyMode) {
      shellError = readOnlyModeMessage(eventType === 'accepted' ? 'Version acceptance' : 'Version review');
      return;
    }

    const targetSlideId = sourceSlideId ?? selectedSlide?.id;
    if (!targetSlideId) return;

    isSubmittingVersionFeedback = true;
    shellError = null;

    try {
      const response = await fetch(deckProductApiPath(`/decks/${graph.deck.id}/slides/${targetSlideId}/feedback`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          slideVersionId: versionId,
          eventType,
          applyToWorkspace
        } satisfies SubmitSlideFeedbackRequest)
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const payload = (await response.json()) as { workspace?: DeckWorkspaceModel };
      if (payload.workspace) {
        workspaceModelState = payload.workspace;
        generationMessage =
          eventType === 'accepted'
            ? 'Generated version applied to the workspace.'
            : 'Generated version marked to keep the original slide.';
      }

      await invalidateAll();
    } catch (error) {
      shellError = error instanceof Error ? error.message : 'Could not save the generated version review.';
    } finally {
      isSubmittingVersionFeedback = false;
    }
  }
</script>

<section class="deck-workspace-shell">
  <DeckShellTopBar
    deck={graph.deck}
    latestBatch={latestBatch}
    {readOnlyMode}
    {backHref}
    {backLabel}
    showPropertiesButton={!readOnlyMode}
    {mode}
    onModeChange={(nextMode) => {
      mode = nextMode;
    }}
    onOpenProperties={() => {
      propertiesOpen = true;
    }}
  />

  {#if shellConfirmation}
    <div class="deck-workspace-shell__confirmation">
      <SaveConfirmationBanner
        title={shellConfirmation.title}
        message={shellConfirmation.message}
        tone={shellConfirmation.tone}
        actionLabel={shellConfirmation.actionLabel}
        actionHref={shellConfirmation.actionHref}
        compact={true}
      />
    </div>
  {/if}

  <div class="deck-workspace-shell__body" class:panel-open={leftPanelOpen}>
    <DeckToolRail {activeTool} {leftPanelOpen} onSelectTool={changeActiveTool} onTogglePanel={toggleLeftPanel} />

    {#if leftPanelOpen}
      <DeckLeftPanel
        {graph}
        properties={propertiesState}
        {activeTool}
        {workspaceHrefBase}
        {selectedSlideId}
        {selectedSlideIds}
        {recommendationCounts}
        {findingSeverities}
        {isAddingSlide}
        allowAddSlide={!readOnlyMode}
        onToggleSlideSelection={toggleSlideSelection}
        onSelectSlide={persistSelectedSlide}
        onSelectAll={selectAllSlides}
        onClearSelection={clearSelectedSlides}
        onAddSlide={addSlide}
      />
    {/if}

    <DeckCanvas
      deck={graph.deck}
      {mode}
      {workspaceHrefBase}
      {selectedSlide}
      {selectedBlocks}
      {selectedBlockId}
      selectedSuggestionsCount={selectedSuggestions.length}
      classificationLookup={classificationLookup}
      thumbnailSlides={graph.slides.slice(0, 8)}
      onSelectBlock={selectBlock}
      onSelectSlide={persistSelectedSlide}
    />

    <div class="deck-workspace-shell__right-column">
      <DeckRightInspector
        slide={selectedSlide}
        block={selectedBlock}
        classification={selectedBlockClassification}
        relatedFindings={selectedBlockFindings}
        relatedSuggestions={selectedBlockSuggestions}
        isSaving={isSavingBlock}
        saveConfirmation={blockSaveMessage}
        onSave={saveSelectedBlock}
      />

      <DeckAiPanel
        latestBatch={latestBatch}
        generationStatus={workspaceModelState.deck.generationStatus}
        {scope}
        {instruction}
        {selectedFindings}
        {selectedSuggestions}
        selectedVersions={selectedGeneratedVersions}
        {canPrepareIteration}
        {preparedIteration}
        isCreatingIteration={isCreatingIteration || isSubmittingVersionFeedback}
        {generationMessage}
        {shellError}
        onScopeChange={(nextScope) => {
          scope = nextScope;
        }}
        onInstructionChange={(nextInstruction) => {
          instruction = nextInstruction;
        }}
        onPrepareIteration={prepareIteration}
        onCreateIteration={createIteration}
        onAcceptGeneratedVersion={(versionId, sourceSlideId) => {
          void submitGeneratedVersionFeedback(versionId, sourceSlideId, 'accepted', true);
        }}
        onRejectGeneratedVersion={(versionId, sourceSlideId) => {
          void submitGeneratedVersionFeedback(versionId, sourceSlideId, 'rejected', false);
        }}
        onOpenSmartEdit={openSmartEdit}
        onOpenBatches={openBatches}
        onOpenChanges={openChanges}
      />
    </div>
  </div>

  <DeckBottomBar
    selectedBlockCount={selectedBlocks.length}
    classificationCount={selectedSlide ? graph.classifications.filter((item) => selectedBlocks.some((block) => block.id === item.blockId)).length : 0}
    revisionCount={graph.revisions.length}
    latestBatch={latestBatch}
  />

  {#if !chatOpen}
    <button
      type="button"
      class="deck-workspace-shell__chat-toggle button"
      onclick={() => {
        toggleChatPopup(true);
      }}
    >
      AI Assistant
    </button>
  {/if}

  <DeckAiChatPopup
    open={chatOpen}
    deckTitle={graph.deck.title}
    slideCount={graph.slides.length}
    contextLabel={graph.deck.purpose}
    currentSlideTitle={selectedSlide?.title}
    selectedSlideCount={selectedSlideIds.length}
    target={chatTarget}
    instruction={chatInstruction}
    preset={chatPreset}
    isCreating={isCreatingIteration}
    onClose={() => {
      toggleChatPopup(false);
    }}
    onTargetChange={(nextTarget) => {
      chatTarget = nextTarget;
    }}
    onInstructionChange={(nextInstruction) => {
      chatInstruction = nextInstruction;
    }}
    onPresetChange={(nextPreset) => {
      chatPreset = nextPreset;
    }}
    onCreateVersion={createVersionFromChat}
  />

  {#if propertiesOpen}
    <div
      class="deck-workspace-shell__drawer-backdrop"
      role="presentation"
      onclick={() => {
        propertiesOpen = false;
      }}
    ></div>
    <div class="deck-workspace-shell__drawer">
      <SmartDeckPropertiesDrawer
        open={true}
        deck={graph.deck}
        properties={propertiesState}
        slides={graph.slides}
        blocks={graph.blocks}
        classifications={graph.classifications}
        findings={graph.findings}
        suggestions={graph.suggestions}
        revisions={graph.revisions}
        isSaving={isSavingProperties}
        saveConfirmation={saveMessage}
        onSave={persistProperties}
      />
      <button
        type="button"
        class="deck-workspace-shell__drawer-close"
        onclick={() => {
          propertiesOpen = false;
        }}
      >
        Close
      </button>
    </div>
  {/if}
</section>

<style>
  .deck-workspace-shell {
    display: grid;
    gap: 1rem;
    position: relative;
  }

  .deck-workspace-shell__confirmation {
    max-width: min(760px, 100%);
  }

  .deck-workspace-shell__body {
    display: grid;
    grid-template-columns: 88px minmax(0, 1fr) 360px;
    gap: 1rem;
    align-items: start;
  }

  .deck-workspace-shell__body.panel-open {
    grid-template-columns: 88px 300px minmax(0, 1fr) 360px;
  }

  .deck-workspace-shell__right-column {
    display: grid;
    gap: 1rem;
    align-content: start;
  }

  .deck-workspace-shell__drawer-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(2, 8, 23, 0.52);
    z-index: 50;
  }

  .deck-workspace-shell__drawer {
    position: fixed;
    top: 1rem;
    right: 1rem;
    width: min(420px, calc(100vw - 2rem));
    z-index: 60;
    display: grid;
    gap: 0.75rem;
  }

  .deck-workspace-shell__drawer-close {
    justify-self: end;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-input);
    color: var(--ink);
    padding: 0.55rem 0.9rem;
  }

  .deck-workspace-shell__drawer-close:disabled {
    opacity: 0.65;
  }

  .deck-workspace-shell__chat-toggle {
    position: fixed;
    right: 1.25rem;
    bottom: 1.25rem;
    z-index: 64;
    box-shadow: var(--shadow-glow-blue);
  }

  @media (max-width: 1320px) {
    .deck-workspace-shell__body {
      grid-template-columns: 88px minmax(0, 1fr);
    }

    .deck-workspace-shell__body.panel-open {
      grid-template-columns: 88px 260px minmax(0, 1fr);
    }

    .deck-workspace-shell__body :global(.deck-ai-panel) {
      grid-column: 1 / -1;
    }
  }

  @media (max-width: 1080px) {
    .deck-workspace-shell__body {
      grid-template-columns: 1fr;
    }

    .deck-workspace-shell__body.panel-open {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 720px) {
    .deck-workspace-shell__confirmation {
      max-width: 100%;
    }

    .deck-workspace-shell__chat-toggle {
      right: 1rem;
      bottom: 1rem;
    }
  }
</style>
