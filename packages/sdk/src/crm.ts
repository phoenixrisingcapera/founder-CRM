import { ApiClient } from './client';
import type {
  CrmActionDecisionRecord,
  CrmAuditEventRecord,
  CrmContactRecord,
  CrmGoalRecord,
  CrmImportStatusRecord,
  CrmInteractionRecord,
  CrmModelDatasetExportRecord,
  CrmModelDatasetExportHistoryRecord,
  CrmModelDatasetManifestRecord,
  CrmModelDatasetProfileRecord,
  CrmModelDatasetRowRecord,
  CrmModelDatasetSummaryRecord,
  CrmModelTrainingBatchCreateRecord,
  CrmModelTrainingBatchRecord,
  CrmModelTrainingBatchSummaryRecord,
  CrmModelTrainingBatchUpdateRecord,
  CrmOverviewRecord,
  CrmRelationshipRecord,
  CrmScoringRecord,
  CrmSettingsRecord,
} from '../../types/src/crm';

export function getCrmOverview(client = new ApiClient()): Promise<CrmOverviewRecord> {
  return client.get<CrmOverviewRecord>('/crm/overview');
}

export function listCrmContacts(client = new ApiClient()): Promise<CrmContactRecord[]> {
  return client.get<CrmContactRecord[]>('/crm/contacts');
}

export function listCrmAuditEvents(
  client = new ApiClient(),
  options?: { limit?: number | null; eventType?: string; entityType?: string },
): Promise<CrmAuditEventRecord[]> {
  const params = new URLSearchParams();
  if (typeof options?.limit === 'number') {
    params.set('limit', String(options.limit));
  }
  if (options?.eventType) params.set('event_type', options.eventType);
  if (options?.entityType) params.set('entity_type', options.entityType);
  const query = params.toString();
  return client.get<CrmAuditEventRecord[]>(`/crm/audit/logs${query ? `?${query}` : ''}`);
}

export function listCrmActionDecisions(
  client = new ApiClient(),
  options?: { contactId?: string; goalId?: string; limit?: number | null },
): Promise<CrmActionDecisionRecord[]> {
  const params = new URLSearchParams();
  if (options?.contactId) params.set('contact_id', options.contactId);
  if (options?.goalId) params.set('goal_id', options.goalId);
  if (options?.limit !== null && options?.limit !== undefined) params.set('limit', String(options.limit));
  const query = params.toString();
  return client.get<CrmActionDecisionRecord[]>(`/crm/actions/decisions${query ? `?${query}` : ''}`);
}

export function listCrmLatestActionDecisionsByContact(
  client = new ApiClient(),
  options?: { contactId?: string; goalId?: string },
): Promise<CrmActionDecisionRecord[]> {
  const params = new URLSearchParams();
  if (options?.contactId) params.set('contact_id', options.contactId);
  if (options?.goalId) params.set('goal_id', options.goalId);
  const query = params.toString();
  return client.get<CrmActionDecisionRecord[]>(`/crm/actions/decisions/latest-by-contact${query ? `?${query}` : ''}`);
}

export function createCrmActionDecision(
  payload: Record<string, unknown>,
  client = new ApiClient(),
): Promise<CrmActionDecisionRecord> {
  return client.post<CrmActionDecisionRecord>('/crm/actions/decisions', payload);
}

export function listCrmGoals(client = new ApiClient()): Promise<CrmGoalRecord[]> {
  return client.get<CrmGoalRecord[]>('/crm/goals');
}

export function listCrmRelationships(client = new ApiClient()): Promise<CrmRelationshipRecord[]> {
  return client.get<CrmRelationshipRecord[]>('/crm/relationships');
}

export function listCrmInteractions(client = new ApiClient()): Promise<CrmInteractionRecord[]> {
  return client.get<CrmInteractionRecord[]>('/crm/interactions');
}

export function getCrmScoring(goalId: string, client = new ApiClient()): Promise<CrmScoringRecord> {
  return client.get<CrmScoringRecord>(`/crm/scoring/${goalId}`);
}

export function getCrmImportStatus(client = new ApiClient()): Promise<CrmImportStatusRecord> {
  return client.get<CrmImportStatusRecord>('/crm/import');
}

export function getCrmSettings(client = new ApiClient()): Promise<CrmSettingsRecord> {
  return client.get<CrmSettingsRecord>('/crm/settings');
}

export function getCrmModelDatasetRows(
  client = new ApiClient(),
  options?: { limit?: number | null; goalId?: string; contactId?: string; verificationStatus?: string; latestOnly?: boolean; staleState?: string },
): Promise<CrmModelDatasetRowRecord[]> {
  const params = new URLSearchParams();
  if (typeof options?.limit === 'number') {
    params.set('limit', String(options.limit));
  }
  if (options?.goalId) params.set('goal_id', options.goalId);
  if (options?.contactId) params.set('contact_id', options.contactId);
  if (options?.verificationStatus) params.set('verification_status', options.verificationStatus);
  if (typeof options?.latestOnly === 'boolean') params.set('latest_only', String(options.latestOnly));
  if (options?.staleState && options.staleState !== 'all') params.set('stale_state', options.staleState);
  const query = params.toString();
  return client.get<CrmModelDatasetRowRecord[]>(`/crm/model-dataset${query ? `?${query}` : ''}`);
}

export function getCrmLatestModelDatasetRowsByContact(
  client = new ApiClient(),
  options?: { goalId?: string; verificationStatus?: string; staleState?: string },
): Promise<CrmModelDatasetRowRecord[]> {
  const params = new URLSearchParams();
  if (options?.goalId) params.set('goal_id', options.goalId);
  if (options?.verificationStatus) params.set('verification_status', options.verificationStatus);
  if (options?.staleState && options.staleState !== 'all') params.set('stale_state', options.staleState);
  const query = params.toString();
  return client.get<CrmModelDatasetRowRecord[]>(`/crm/model-dataset/latest-by-contact${query ? `?${query}` : ''}`);
}

export function getCrmModelDatasetSummary(
  client = new ApiClient(),
  options?: { goalId?: string; verificationStatus?: string; latestOnly?: boolean; staleState?: string },
): Promise<CrmModelDatasetSummaryRecord> {
  const params = new URLSearchParams();
  if (options?.goalId) params.set('goal_id', options.goalId);
  if (options?.verificationStatus) params.set('verification_status', options.verificationStatus);
  if (typeof options?.latestOnly === 'boolean') params.set('latest_only', String(options.latestOnly));
  if (options?.staleState && options.staleState !== 'all') params.set('stale_state', options.staleState);
  const query = params.toString();
  return client.get<CrmModelDatasetSummaryRecord>(`/crm/model-dataset/summary${query ? `?${query}` : ''}`);
}

export function exportCrmModelDataset(
  client = new ApiClient(),
  options?: { limit?: number | null; goalId?: string; verificationStatus?: string; latestOnly?: boolean; staleState?: string },
): Promise<string> {
  const params = new URLSearchParams();
  if (typeof options?.limit === 'number') {
    params.set('limit', String(options.limit));
  }
  if (options?.goalId) params.set('goal_id', options.goalId);
  if (options?.verificationStatus) params.set('verification_status', options.verificationStatus);
  if (typeof options?.latestOnly === 'boolean') params.set('latest_only', String(options.latestOnly));
  if (options?.staleState && options.staleState !== 'all') params.set('stale_state', options.staleState);
  const query = params.toString();
  return client.getText(`/crm/model-dataset/export${query ? `?${query}` : ''}`);
}

export function recordCrmModelDatasetExport(
  payload: CrmModelDatasetExportRecord,
  client = new ApiClient(),
): Promise<CrmAuditEventRecord> {
  return client.post<CrmAuditEventRecord>('/crm/model-dataset/export-records', payload);
}

export function listCrmModelDatasetExportRecords(
  client = new ApiClient(),
  options?: { limit?: number | null; goalId?: string; verificationStatus?: string; latestOnly?: boolean; staleState?: string },
): Promise<CrmModelDatasetExportHistoryRecord[]> {
  const params = new URLSearchParams();
  if (typeof options?.limit === 'number') {
    params.set('limit', String(options.limit));
  }
  if (options?.goalId) params.set('goal_id', options.goalId);
  if (options?.verificationStatus) params.set('verification_status', options.verificationStatus);
  if (typeof options?.latestOnly === 'boolean') params.set('latest_only', String(options.latestOnly));
  if (options?.staleState && options.staleState !== 'all') params.set('stale_state', options.staleState);
  const query = params.toString();
  return client.get<CrmModelDatasetExportHistoryRecord[]>(`/crm/model-dataset/export-records${query ? `?${query}` : ''}`);
}

export function createCrmModelTrainingBatch(
  payload: CrmModelTrainingBatchCreateRecord,
  client = new ApiClient(),
): Promise<CrmModelTrainingBatchRecord> {
  return client.post<CrmModelTrainingBatchRecord>('/crm/model-dataset/training-batches', payload);
}

export function listCrmModelTrainingBatches(
  client = new ApiClient(),
  options?: { limit?: number | null; goalId?: string; verificationStatus?: string; latestOnly?: boolean; staleState?: string; status?: string },
): Promise<CrmModelTrainingBatchRecord[]> {
  const params = new URLSearchParams();
  if (typeof options?.limit === 'number') {
    params.set('limit', String(options.limit));
  }
  if (options?.goalId) params.set('goal_id', options.goalId);
  if (options?.verificationStatus) params.set('verification_status', options.verificationStatus);
  if (typeof options?.latestOnly === 'boolean') params.set('latest_only', String(options.latestOnly));
  if (options?.staleState && options.staleState !== 'all') params.set('stale_state', options.staleState);
  if (options?.status) params.set('status', options.status);
  const query = params.toString();
  return client.get<CrmModelTrainingBatchRecord[]>(`/crm/model-dataset/training-batches${query ? `?${query}` : ''}`);
}

export function getActiveCrmModelTrainingBatch(
  client = new ApiClient(),
  options?: { goalId?: string; verificationStatus?: string; latestOnly?: boolean; staleState?: string },
): Promise<CrmModelTrainingBatchRecord | null> {
  const params = new URLSearchParams();
  if (options?.goalId) params.set('goal_id', options.goalId);
  if (options?.verificationStatus) params.set('verification_status', options.verificationStatus);
  if (typeof options?.latestOnly === 'boolean') params.set('latest_only', String(options.latestOnly));
  if (options?.staleState && options.staleState !== 'all') params.set('stale_state', options.staleState);
  const query = params.toString();
  return client.get<CrmModelTrainingBatchRecord | null>(`/crm/model-dataset/training-batches/active${query ? `?${query}` : ''}`);
}

export function getCrmModelTrainingBatchSummary(
  client = new ApiClient(),
): Promise<CrmModelTrainingBatchSummaryRecord> {
  return client.get<CrmModelTrainingBatchSummaryRecord>('/crm/model-dataset/training-batches/summary');
}

export function updateCrmModelTrainingBatch(
  batchId: string,
  payload: CrmModelTrainingBatchUpdateRecord,
  client = new ApiClient(),
): Promise<CrmModelTrainingBatchRecord> {
  return client.patch<CrmModelTrainingBatchRecord>(`/crm/model-dataset/training-batches/${batchId}`, payload);
}

export function getCrmModelDatasetProfile(
  client = new ApiClient(),
  options?: { goalId?: string; verificationStatus?: string; latestOnly?: boolean; staleState?: string },
): Promise<CrmModelDatasetProfileRecord> {
  const params = new URLSearchParams();
  if (options?.goalId) params.set('goal_id', options.goalId);
  if (options?.verificationStatus) params.set('verification_status', options.verificationStatus);
  if (typeof options?.latestOnly === 'boolean') params.set('latest_only', String(options.latestOnly));
  if (options?.staleState && options.staleState !== 'all') params.set('stale_state', options.staleState);
  const query = params.toString();
  return client.get<CrmModelDatasetProfileRecord>(`/crm/model-dataset/profile${query ? `?${query}` : ''}`);
}

export function getCrmModelDatasetManifest(
  client = new ApiClient(),
  options?: { goalId?: string; verificationStatus?: string; latestOnly?: boolean; staleState?: string },
): Promise<CrmModelDatasetManifestRecord> {
  const params = new URLSearchParams();
  if (options?.goalId) params.set('goal_id', options.goalId);
  if (options?.verificationStatus) params.set('verification_status', options.verificationStatus);
  if (typeof options?.latestOnly === 'boolean') params.set('latest_only', String(options.latestOnly));
  if (options?.staleState && options.staleState !== 'all') params.set('stale_state', options.staleState);
  const query = params.toString();
  return client.get<CrmModelDatasetManifestRecord>(`/crm/model-dataset/manifest${query ? `?${query}` : ''}`);
}

export function captureLinkedInProfileUrl(
  payload: Record<string, unknown>,
  client = new ApiClient(),
): Promise<CrmContactRecord> {
  return client.post<CrmContactRecord>('/crm/contacts', payload);
}

export function importManualCrmContact(
  payload: Record<string, unknown>,
  client = new ApiClient(),
): Promise<CrmContactRecord> {
  return client.post<CrmContactRecord>('/crm/contacts', payload);
}

export function runCrmScoring(goalId: string, client = new ApiClient()): Promise<CrmScoringRecord> {
  return client.post<CrmScoringRecord>(`/crm/scoring/${goalId}/run`, {});
}
