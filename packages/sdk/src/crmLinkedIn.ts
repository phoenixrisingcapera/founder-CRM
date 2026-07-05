import { ApiClient } from './client';
import type {
  LinkedInCaptureRecord,
  LinkedInConnectedProfileRecord,
  LinkedInConnectorStateRecord,
  LinkedInLiveReadinessRecord,
  LinkedInManualImportPayload,
  LinkedInOAuthStartRecord,
  LinkedInProvenanceSummaryRecord,
  LinkedInProfileUrlCapturePayload,
} from '../../types/src/linkedin';

export function captureLinkedInProfileUrl(
  payload: LinkedInProfileUrlCapturePayload,
  client = new ApiClient(),
): Promise<LinkedInCaptureRecord> {
  return client.post<LinkedInCaptureRecord>('/crm/connectors/linkedin/profile-url', payload);
}

export function importManualLinkedInContact(
  payload: LinkedInManualImportPayload,
  client = new ApiClient(),
): Promise<LinkedInCaptureRecord> {
  return client.post<LinkedInCaptureRecord>('/crm/imports/manual', payload);
}

export function getLinkedInConnectorState(client = new ApiClient()): Promise<LinkedInConnectorStateRecord> {
  return client.get<LinkedInConnectorStateRecord>('/crm/connectors/linkedin/status');
}

export function getLinkedInOAuthStart(client = new ApiClient()): Promise<LinkedInOAuthStartRecord> {
  return client.get<LinkedInOAuthStartRecord>('/crm/connectors/linkedin/oauth/start');
}

export function getLinkedInConnectedProfile(client = new ApiClient()): Promise<LinkedInConnectedProfileRecord> {
  return client.get<LinkedInConnectedProfileRecord>('/crm/connectors/linkedin/me');
}

export function getLinkedInProvenanceSummary(client = new ApiClient()): Promise<LinkedInProvenanceSummaryRecord> {
  return client.get<LinkedInProvenanceSummaryRecord>('/crm/connectors/linkedin/summary');
}

export function getLinkedInLiveReadiness(client = new ApiClient()): Promise<LinkedInLiveReadinessRecord> {
  return client.get<LinkedInLiveReadinessRecord>('/crm/connectors/linkedin/readiness');
}
