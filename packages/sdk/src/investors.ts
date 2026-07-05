import { ApiClient } from './client';
import type { InvestorRecord } from '../../types/src/investor';

export function listInvestors(client = new ApiClient()): Promise<InvestorRecord[]> {
  return client.get<InvestorRecord[]>('/investors');
}

export function getInvestor(investorId: string, client = new ApiClient()): Promise<InvestorRecord> {
  return client.get<InvestorRecord>(`/investors/${investorId}`);
}
