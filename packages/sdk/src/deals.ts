import { ApiClient } from './client';
import type { DealRecord } from '../../types/src/deal';

export function listDeals(client = new ApiClient()): Promise<DealRecord[]> {
  return client.get<DealRecord[]>('/deals');
}

export function getDeal(dealId: string, client = new ApiClient()): Promise<DealRecord> {
  return client.get<DealRecord>(`/deals/${dealId}`);
}

export function createDeal(
  payload: {
    company_id: string;
    project_id?: string | null;
    name: string;
    status?: string;
    stage?: string;
    thesis_fit?: string;
  },
  client = new ApiClient(),
): Promise<DealRecord> {
  return client.post<DealRecord>('/deals', payload);
}
