import { ApiClient } from './client';
import type { CrmScoreRunRecord, CrmScoringRecord } from '../../types/src/crm';

export function getCrmGoalScores(goalId: string, client = new ApiClient()): Promise<CrmScoringRecord> {
  return client.get<CrmScoringRecord>(`/crm/goals/${goalId}/scores`);
}

export function listCrmGoalScoreRuns(
  goalId: string,
  client = new ApiClient(),
  limit?: number | null,
): Promise<CrmScoreRunRecord[]> {
  const params = new URLSearchParams();
  if (typeof limit === 'number') params.set('limit', String(limit));
  const query = params.toString();
  return client.get<CrmScoreRunRecord[]>(`/crm/goals/${goalId}/score-runs${query ? `?${query}` : ''}`);
}

export function getCrmScoreRun(
  scoreRunId: string,
  client = new ApiClient(),
): Promise<CrmScoringRecord> {
  return client.get<CrmScoringRecord>(`/crm/score-runs/${scoreRunId}`);
}
