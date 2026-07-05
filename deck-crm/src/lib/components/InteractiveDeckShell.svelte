<script lang="ts">
  import type { DeckShellProperties, DeckWorkspaceModel, DeckWorkspacePreferences, DesignBatchPreview, SaveConfirmation } from '@deck-aistack-codes/shared';
  import DeckWorkspaceShell from '$components/deck-shell/DeckWorkspaceShell.svelte';
  import type { DeckGraph } from '$types/domain';

  interface Props {
    graph: DeckGraph;
    workspaceModel: DeckWorkspaceModel;
    properties?: DeckShellProperties;
    workspacePreferences?: DeckWorkspacePreferences;
    selectedSlideId?: string;
    latestBatches?: DesignBatchPreview[];
    latestConfirmation?: SaveConfirmation | null;
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
    latestConfirmation = null,
    workspaceHrefBase,
    readOnlyMode = false,
    backHref,
    backLabel
  }: Props = $props();

  const effectiveReadOnlyMode = $derived(
    readOnlyMode || workspaceHrefBase?.includes('/smart-deck') === true
  );
</script>

<DeckWorkspaceShell
  {graph}
  {workspaceModel}
  {properties}
  {workspacePreferences}
  {selectedSlideId}
  {latestBatches}
  initialShellConfirmation={latestConfirmation}
  {workspaceHrefBase}
  readOnlyMode={effectiveReadOnlyMode}
  {backHref}
  {backLabel}
/>
