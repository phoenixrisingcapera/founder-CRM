import type { CrmModelDatasetRowRecord } from './crm';

export type LinkedInReasonCode =
  | 'ROLE_MATCH'
  | 'SECTOR_MATCH'
  | 'THESIS_MATCH'
  | 'WARM_INTRO_AVAILABLE'
  | 'DIRECT_RELATIONSHIP'
  | 'LOW_CONFIDENCE_DATA'
  | 'NO_INTRO_PATH';

export interface LinkedInProfileUrlCapturePayload {
  profile_url: string;
  name: string;
  role_headline?: string;
  organisation?: string;
  notes?: string;
}

export interface LinkedInManualImportPayload extends LinkedInProfileUrlCapturePayload {
  contact_type?: string;
}

export interface LinkedInCaptureRecord {
  id?: string;
  profile_url: string;
  name: string;
  role_headline?: string | null;
  organisation?: string | null;
  notes?: string | null;
  source_type: string;
  verification_status: string;
  created_at?: string;
  linkedin_source_payload_json?: Record<string, unknown> | null;
  linkedin_last_synced_at?: string | null;
}

export interface LinkedInConnectorStateRecord {
  connector: string;
  status: string;
  supported_mode: string;
  notes: string;
  provider: string;
  live_data_enabled: boolean;
  oauth_ready: boolean;
  blocker_reason?: string | null;
  required_env: string[];
  live_data_blocker_reason?: string | null;
  live_data_required_env: string[];
  oauth_blocker_reason?: string | null;
  oauth_required_env: string[];
  connected_member_name?: string | null;
  connected_member_email?: string | null;
  connected_at?: string | null;
}

export interface LinkedInOAuthStartRecord {
  ready: boolean;
  authorization_url?: string | null;
  redirect_uri?: string | null;
  frontend_callback_path?: string | null;
  frontend_callback_url?: string | null;
  redirect_uri_uses_frontend_callback?: boolean;
  redirect_uri_matches_frontend_callback_url?: boolean;
  scopes: string[];
  state?: string | null;
  blocker_reason?: string | null;
  required_env: string[];
}

export interface LinkedInConnectedProfileRecord {
  connected: boolean;
  provider: string;
  member_id?: string | null;
  name?: string | null;
  email?: string | null;
  headline?: string | null;
  picture_url?: string | null;
  profile_url?: string | null;
  connected_at?: string | null;
  expires_at?: string | null;
}

export interface LinkedInProvenanceContactSummaryRecord {
  contact_id: string;
  full_name: string;
  primary_organisation?: string | null;
  profile_url?: string | null;
  source_type?: string | null;
  verification_status?: string | null;
  capture_mode?: string | null;
  linkedin_last_synced_at?: string | null;
  updated_at: string;
}

export interface LinkedInProvenanceSummaryRecord {
  total_linkedin_contacts: number;
  manual_capture_count: number;
  manual_import_count: number;
  provider_verified_count: number;
  unverified_count: number;
  latest_sync_at?: string | null;
  recent_contacts: LinkedInProvenanceContactSummaryRecord[];
}

export interface LinkedInLiveReadinessRecord {
  stage: string;
  recommended_test_path: string;
  next_steps: string[];
  provider_ready: boolean;
  oauth_ready: boolean;
  blocker_reason?: string | null;
  provider_blocker_reason?: string | null;
  oauth_blocker_reason?: string | null;
  required_env: string[];
  provider_required_env: string[];
  oauth_required_env: string[];
  connected_member_ready: boolean;
  provider_verified_count: number;
  provider_verified_model_ready_count: number;
  provider_verified_model_stale_count: number;
  provider_verified_scoring_pending_count: number;
  total_linkedin_contacts: number;
  latest_sync_at?: string | null;
  latest_provider_verified_contact?: LinkedInProvenanceContactSummaryRecord | null;
  latest_provider_verified_contact_model_ready: boolean;
  latest_provider_verified_contact_model_stale: boolean;
  latest_provider_verified_model_row?: CrmModelDatasetRowRecord | null;
}

export interface LinkedInIntroPathSearchPayload {
  goal_id: string;
  contact_id: string;
}

export interface LinkedInIntroPathRecord {
  id: string;
  contact_id: string;
  contact_name: string;
  path_label: string;
  hop_count: number;
  path_strength: number;
  confidence: number;
  nodes: string[];
}

export interface LinkedInMergeSuggestionRecord {
  id: string;
  imported_contact_id: string;
  existing_contact_id: string;
  imported_name: string;
  existing_contact_name: string;
  existing_organisation?: string | null;
  confidence: number;
  reason: string;
  status: string;
}
