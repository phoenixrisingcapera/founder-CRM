import { ApiClient } from './client';
import type { CompanyRecord } from '../../types/src/company';

export function listCompanies(client = new ApiClient()): Promise<CompanyRecord[]> {
  return client.get<CompanyRecord[]>('/companies');
}

export function getCompany(companyId: string, client = new ApiClient()): Promise<CompanyRecord> {
  return client.get<CompanyRecord>(`/companies/${companyId}`);
}

export function createCompany(
  payload: {
    name: string;
    project_id?: string | null;
    website?: string;
    sector?: string;
    stage?: string;
    geography?: string;
  },
  client = new ApiClient(),
): Promise<CompanyRecord> {
  return client.post<CompanyRecord>('/companies', payload);
}
