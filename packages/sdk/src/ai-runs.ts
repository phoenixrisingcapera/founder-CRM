import { ApiClient } from './client';

export interface AIRunRecord {
  id: string;
  skill_name: string;
  status: string;
  entity_type?: string | null;
  entity_id?: string | null;
  created_at?: string;
}

export function listAiRuns(client = new ApiClient()): Promise<AIRunRecord[]> {
  return client.get<AIRunRecord[]>('/ai-runs');
}

