import { ApiClient } from './client';

export interface AugmentationRunRecord {
  run_id: string;
  target_type: string;
  target_id: string;
  status: string;
  focus: string;
  summary: string;
  insights: Array<{ label: string; value: string; confidence: string }>;
  next_actions: Array<{ title: string; body: string }>;
  provenance: string[];
}

export function augmentCompany(companyId: string, payload: Record<string, unknown>, client = new ApiClient()) {
  return client.post<AugmentationRunRecord>(`/companies/${companyId}/augment`, payload);
}

export function augmentFounder(founderId: string, payload: Record<string, unknown>, client = new ApiClient()) {
  return client.post<AugmentationRunRecord>(`/founders/${founderId}/augment`, payload);
}

export function augmentInvestor(investorId: string, payload: Record<string, unknown>, client = new ApiClient()) {
  return client.post<AugmentationRunRecord>(`/investors/${investorId}/augment`, payload);
}

export function augmentSource(sourceId: string, payload: Record<string, unknown>, client = new ApiClient()) {
  return client.post<AugmentationRunRecord>(`/sources/${sourceId}/augment`, payload);
}

export function getAugmentationRun(runId: string, client = new ApiClient()) {
  return client.get<AugmentationRunRecord>(`/augmentation-runs/${runId}`);
}
