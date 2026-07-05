import { ApiClient } from './client';
import type { FounderRecord } from '../../types/src/founder';

export function listFounders(
  options: { companyId?: string } = {},
  client = new ApiClient(),
): Promise<FounderRecord[]> {
  const params = new URLSearchParams();
  if (options.companyId) {
    params.set('company_id', options.companyId);
  }
  const suffix = params.size ? `?${params.toString()}` : '';
  return client.get<FounderRecord[]>(`/founders${suffix}`);
}

export function getFounder(founderId: string, client = new ApiClient()): Promise<FounderRecord> {
  return client.get<FounderRecord>(`/founders/${founderId}`);
}

export function createFounder(
  payload: {
    company_id: string;
    name: string;
    title?: string;
    linkedin_url?: string;
    bio?: string;
  },
  client = new ApiClient(),
): Promise<FounderRecord> {
  return client.post<FounderRecord>('/founders', payload);
}
