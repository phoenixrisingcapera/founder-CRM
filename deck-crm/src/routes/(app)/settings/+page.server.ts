import { error } from '@sveltejs/kit';
import { deckProductApiPath } from '$lib/contracts';

export async function load({ fetch, locals }) {
  const [workspaceResponse, settingsResponse] = await Promise.all([
    fetch(deckProductApiPath('/workspace-summary')),
    fetch('/api/settings/account/connected-accounts')
  ]);
  const workspacePayload = await workspaceResponse.json().catch(() => null);
  const settingsPayload = await settingsResponse.json().catch(() => null);

  if (!workspaceResponse.ok || !workspacePayload?.workspace) {
    throw error(workspaceResponse.status || 503, workspacePayload?.message ?? 'Could not load workspace settings.');
  }
  if (!settingsResponse.ok || !settingsPayload?.settings) {
    throw error(settingsResponse.status || 503, settingsPayload?.message ?? 'Could not load account settings.');
  }

  return {
    workspace: workspacePayload.workspace,
    settings: settingsPayload.settings,
    inspection: locals.founderInspection
  };
}
