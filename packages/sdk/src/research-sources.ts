import { ApiClient } from './client';
import type { ResearchSourceRecord, SourceSnapshotRecord } from '../../types/src/research-source';

export function listResearchSources(client = new ApiClient()): Promise<ResearchSourceRecord[]> {
  return client.get<ResearchSourceRecord[]>('/research-sources');
}

export function listSourceSnapshots(
  sourceId: string,
  client = new ApiClient(),
): Promise<SourceSnapshotRecord[]> {
  return client.get<SourceSnapshotRecord[]>(`/research-sources/${sourceId}/snapshots`);
}
