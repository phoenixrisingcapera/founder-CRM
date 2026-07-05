import { ApiClient } from './client';
import type { WorkspaceSummaryRecord } from '../../types/src/workspace';

export function getCurrentWorkspaceSummary(
  client = new ApiClient(),
): Promise<WorkspaceSummaryRecord> {
  return client.get<WorkspaceSummaryRecord>('/workspaces/current/summary');
}
