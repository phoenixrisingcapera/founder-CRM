import { ApiClient } from './client';
import type { CrmGoalRecord, CrmScoringRecord } from '../../types/src/crm';

export function listCrmGoals(client = new ApiClient()): Promise<CrmGoalRecord[]> {
  return client.get<CrmGoalRecord[]>('/crm/goals');
}

export function createCrmGoal(
  payload: {
    title: string;
    description?: string;
    goal_type?: string;
    target_persona?: string;
    target_sector?: string;
    status?: string;
  },
  client = new ApiClient(),
): Promise<CrmGoalRecord> {
  return client.post<CrmGoalRecord>('/crm/goals', payload);
}

export function scoreCrmGoal(goalId: string, client = new ApiClient()): Promise<CrmScoringRecord> {
  return client.post<CrmScoringRecord>(`/crm/goals/${goalId}/score`, {});
}
