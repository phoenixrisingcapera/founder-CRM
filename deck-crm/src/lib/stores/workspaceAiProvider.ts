import { writable } from 'svelte/store';
import type { WorkspaceAiProviderRouteResponse } from '@deck-aistack-codes/shared';
import { deckServiceClient } from '$lib/api/deckServiceClient';

export const workspaceAiProviderStore = writable<WorkspaceAiProviderRouteResponse['summary'] | null>(null);

let workspaceAiProviderLoadPromise: Promise<WorkspaceAiProviderRouteResponse['summary'] | null> | null = null;
let workspaceAiProviderLoaded = false;

export function setWorkspaceAiProviderSummary(summary: WorkspaceAiProviderRouteResponse['summary'] | null) {
  workspaceAiProviderLoaded = true;
  workspaceAiProviderStore.set(summary);
}

export async function loadWorkspaceAiProviderSummary() {
  if (workspaceAiProviderLoaded) {
    return new Promise<WorkspaceAiProviderRouteResponse['summary'] | null>((resolve) => {
      workspaceAiProviderStore.subscribe((value) => resolve(value))();
    });
  }

  if (!workspaceAiProviderLoadPromise) {
    workspaceAiProviderLoadPromise = deckServiceClient.getWorkspaceAiProvider()
      .then((payload) => {
        workspaceAiProviderLoaded = true;
        workspaceAiProviderStore.set(payload.summary);
        return payload.summary;
      })
      .catch(() => {
        workspaceAiProviderLoaded = true;
        workspaceAiProviderStore.set(null);
        return null;
      })
      .finally(() => {
        workspaceAiProviderLoadPromise = null;
      });
  }

  return workspaceAiProviderLoadPromise;
}
