import { ApiClient } from './client';

export interface ResearchQueryMatchRecord {
  source_id: string;
  source_title: string;
  snapshot_id?: string | null;
  chunk_id?: string | null;
  title: string;
  excerpt: string;
  score: number;
  locator?: string | null;
}

export interface ResearchQueryResponseRecord {
  query: string;
  total_matches: number;
  matches: ResearchQueryMatchRecord[];
}

export function searchResearch(
  payload: { query: string; limit?: number },
  client = new ApiClient(),
): Promise<ResearchQueryResponseRecord> {
  return client.post<ResearchQueryResponseRecord>('/research-queries/search', payload);
}
