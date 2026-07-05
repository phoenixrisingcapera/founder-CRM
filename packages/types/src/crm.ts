export interface CrmContactRecord {
  id: string;
  created_at: string;
  updated_at: string;
  organisation_id: string;
  created_by: string;
  full_name: string;
  primary_organisation?: string | null;
  role_title?: string | null;
  contact_kind: string;
  linkedin_url?: string | null;
  source_type?: string | null;
  verification_status?: string | null;
  linkedin_source_payload_json?: Record<string, unknown> | null;
  linkedin_last_synced_at?: string | null;
  email?: string | null;
  geography?: string | null;
  status: string;
  notes?: string | null;
}

export interface CrmAuditEventRecord {
  id: string;
  created_at: string;
  updated_at: string;
  organisation_id: string;
  created_by: string;
  event_type: string;
  entity_type: string;
  entity_id?: string | null;
  summary: string;
  detail?: string | null;
  payload_json?: Record<string, unknown> | null;
}

export interface CrmActionDecisionRecord {
  id: string;
  created_at: string;
  updated_at: string;
  organisation_id: string;
  created_by: string;
  contact_id: string;
  goal_id?: string | null;
  action_label: string;
  decision_status: 'suggested' | 'queued' | 'completed' | 'dismissed';
  rationale?: string | null;
  source_surface: string;
  source_context_json?: Record<string, unknown> | null;
}

export interface CrmGoalRecord {
  id: string;
  created_at: string;
  updated_at: string;
  organisation_id: string;
  created_by: string;
  title: string;
  description?: string | null;
  goal_type: string;
  target_persona?: string | null;
  target_sector?: string | null;
  status: string;
}

export interface CrmRelationshipRecord {
  id: string;
  created_at: string;
  updated_at: string;
  organisation_id: string;
  created_by: string;
  from_contact_id: string;
  to_contact_id: string;
  relationship_type: string;
  strength_label?: string | null;
  confidence_label?: string | null;
  notes?: string | null;
}

export interface CrmInteractionRecord {
  id: string;
  created_at: string;
  updated_at: string;
  organisation_id: string;
  created_by: string;
  contact_id: string;
  channel: string;
  direction?: string | null;
  subject?: string | null;
  summary: string;
  source_type?: string | null;
  source_label?: string | null;
  source_context_json?: Record<string, unknown> | null;
  happened_at: string;
}

export interface CrmScoreRunRecord {
  id: string;
  created_at: string;
  updated_at: string;
  organisation_id: string;
  created_by: string;
  goal_id: string;
  algorithm_version: string;
  status: string;
}

export interface CrmScoreSignalSnapshotRecord {
  contact_kind?: string | null;
  contact_status?: string | null;
  source_type?: string | null;
  verification_status?: string | null;
  has_email?: boolean;
  has_linkedin_url?: boolean;
  interaction_count?: number;
  recent_interaction_count?: number;
  relationship_count?: number;
  strong_relationship_count?: number;
  linkedin_last_synced_at?: string | null;
}

export interface CrmScoreGoalSnapshotRecord {
  goal_id?: string | null;
  goal_type?: string | null;
  target_persona?: string | null;
  target_sector?: string | null;
}

export interface CrmScoreEvidenceSummaryRecord {
  interaction_ids?: string[];
  relationship_ids?: string[];
  interaction_count?: number;
  relationship_count?: number;
}

export interface CrmScoreOperatorFeedbackRecord {
  decision_count?: number;
  latest_action_label?: string | null;
  latest_decision_status?: string | null;
  latest_source_surface?: string | null;
  latest_decided_at?: string | null;
}

export interface CrmScoreBreakdownRecord {
  fit?: number;
  proximity?: number;
  warmth?: number;
  timing?: number;
  confidence?: number;
  intro_path?: string | null;
  signal_snapshot?: CrmScoreSignalSnapshotRecord;
  goal_snapshot?: CrmScoreGoalSnapshotRecord;
  evidence_summary?: CrmScoreEvidenceSummaryRecord;
  operator_feedback?: CrmScoreOperatorFeedbackRecord;
}

export interface CrmContactScoreRecord {
  id: string;
  created_at: string;
  updated_at: string;
  organisation_id: string;
  score_run_id: string;
  contact_id: string;
  goal_id: string;
  relationship_warmth_score: number;
  fit_score: number;
  proximity_score: number;
  timing_score: number;
  opportunity_score: number;
  confidence_score: number;
  algorithm_version: string;
  reason_codes_json: string[];
  breakdown_json: CrmScoreBreakdownRecord;
  evidence_ids_json: string[];
}

export interface CrmScoringRecord {
  goal: CrmGoalRecord;
  score_run: CrmScoreRunRecord;
  scores: CrmContactScoreRecord[];
}

export interface CrmModelDatasetRowRecord {
  score_id: string;
  score_run: CrmScoreRunRecord;
  goal: CrmGoalRecord;
  contact: CrmContactRecord;
  stale_after_linkedin_sync: boolean;
  opportunity_score: number;
  fit_score: number;
  proximity_score: number;
  relationship_warmth_score: number;
  timing_score: number;
  confidence_score: number;
  reason_codes_json: string[];
  breakdown_json: CrmScoreBreakdownRecord;
  evidence_ids_json: string[];
}

export interface CrmModelDatasetSummaryRecord {
  total_rows: number;
  provider_verified_rows: number;
  stale_rows: number;
  stale_state: string;
  goals_covered: number;
  latest_score_run_at?: string | null;
  latest_row?: CrmModelDatasetRowRecord | null;
}

export interface CrmModelDatasetReasonCountRecord {
  reason_code: string;
  count: number;
}

export interface CrmModelDatasetProfileRecord {
  total_rows: number;
  provider_verified_rows: number;
  stale_rows: number;
  stale_state: string;
  unverified_rows: number;
  operator_feedback_rows: number;
  latest_only: boolean;
  average_opportunity_score: number;
  average_fit_score: number;
  average_confidence_score: number;
  source_type_counts: Record<string, number>;
  top_reason_codes: CrmModelDatasetReasonCountRecord[];
}

export interface CrmModelDatasetManifestRecord {
  generated_at: string;
  algorithm_versions: string[];
  latest_only: boolean;
  stale_state: string;
  goal_id?: string | null;
  verification_status?: string | null;
  total_rows: number;
  goals_covered: number;
  score_run_ids: string[];
  goal_ids: string[];
  source_type_counts: Record<string, number>;
  provider_verified_rows: number;
  stale_rows: number;
  operator_feedback_rows: number;
  export_line_count: number;
  export_bytes: number;
  export_sha256: string;
  export_filename: string;
}

export interface CrmModelDatasetExportRecord {
  goal_id?: string | null;
  verification_status?: string | null;
  latest_only: boolean;
  stale_state: string;
}

export interface CrmModelDatasetExportHistoryRecord {
  id: string;
  created_at: string;
  updated_at: string;
  organisation_id: string;
  created_by: string;
  goal_id?: string | null;
  verification_status?: string | null;
  latest_only: boolean;
  stale_state: string;
  total_rows: number;
  goals_covered: number;
  score_run_ids: string[];
  goal_ids: string[];
  algorithm_versions: string[];
  source_type_counts: Record<string, number>;
  provider_verified_rows: number;
  stale_rows: number;
  operator_feedback_rows: number;
  export_line_count: number;
  export_bytes: number;
  export_sha256: string;
  export_filename: string;
}

export interface CrmModelTrainingBatchCreateRecord {
  goal_id?: string | null;
  verification_status?: string | null;
  latest_only: boolean;
  stale_state: string;
  batch_label?: string | null;
  notes?: string | null;
}

export interface CrmModelTrainingBatchUpdateRecord {
  status: string;
  notes?: string | null;
}

export interface CrmModelTrainingBatchRecord {
  id: string;
  created_at: string;
  updated_at: string;
  organisation_id: string;
  created_by: string;
  goal_id?: string | null;
  verification_status?: string | null;
  latest_only: boolean;
  stale_state: string;
  batch_label: string;
  status: string;
  notes?: string | null;
  total_rows: number;
  goals_covered: number;
  score_run_ids: string[];
  goal_ids: string[];
  algorithm_versions: string[];
  source_type_counts: Record<string, number>;
  provider_verified_rows: number;
  stale_rows: number;
  operator_feedback_rows: number;
  export_line_count: number;
  export_bytes: number;
  export_sha256: string;
  export_filename: string;
}

export interface CrmModelTrainingBatchSummaryRecord {
  total_batches: number;
  staged_batches: number;
  ready_batches: number;
  training_batches: number;
  archived_batches: number;
  active_batch?: CrmModelTrainingBatchRecord | null;
}

export interface CrmOverviewRecord {
  contact_count: number;
  goal_count: number;
  relationship_count: number;
  interaction_count: number;
  scored_contact_count: number;
  highlighted_goal?: string | null;
}

export interface CrmImportSourceRecord {
  source: string;
  status: string;
  notes: string;
}

export interface CrmImportStatusRecord {
  supported_sources: CrmImportSourceRecord[];
}

export interface CrmSettingsRecord {
  algorithm_version: string;
  manual_import_policy: string;
  draft_follow_up_policy: string;
}

export type CrmReasonCode =
  | 'ROLE_MATCH'
  | 'SECTOR_MATCH'
  | 'STAGE_MATCH'
  | 'GEOGRAPHY_MATCH'
  | 'THESIS_MATCH'
  | 'ORGANISATION_MATCH'
  | 'WARM_INTRO_AVAILABLE'
  | 'DIRECT_RELATIONSHIP'
  | 'RECENT_INTERACTION'
  | 'NETWORK_OVERLAP'
  | 'LOW_CONFIDENCE_DATA'
  | 'NO_INTRO_PATH'
  | 'EXCLUDED_BY_TAG';

export interface CrmKpiRecord {
  id: string;
  label: string;
  value: string | number;
  delta_label?: string;
  trend: 'up' | 'down' | 'flat';
  accent: 'green' | 'teal' | 'amber' | 'blue' | 'purple';
}

export interface CrmGoalProgressRecord {
  goal_id: string;
  name: string;
  target_count: number;
  completed_count: number;
  due_date?: string;
  progress_percent: number;
  status: 'draft' | 'active' | 'at_risk' | 'complete' | 'archived';
}

export interface CrmSuggestedActionRecord {
  id: string;
  person_id?: string;
  label: 'request_intro' | 'send_follow_up' | 'add_to_pipeline' | 'add_note' | 'enrich_profile' | 'mark_not_relevant';
  title: string;
  description?: string;
  draft_only: boolean;
  status: 'suggested' | 'queued' | 'completed' | 'dismissed';
}

export interface CrmRankedContactRecord {
  id: string;
  full_name: string;
  role_title?: string | null;
  organisation_name?: string | null;
  geography?: string | null;
  contact_kind: string;
  source_type?: string | null;
  verification_status?: string | null;
  linkedin_last_synced_at?: string | null;
  fit_score: number;
  proximity_score: number;
  relationship_warmth_score: number;
  confidence_score: number;
  opportunity_score: number;
  reason_codes: CrmReasonCode[];
  suggested_action: CrmSuggestedActionRecord;
  model_slice?: {
    goal_id?: string | null;
    score_run_id?: string | null;
    verification_status?: string | null;
    latest_only: boolean;
    stale_state: 'current' | 'stale';
  } | null;
}

export interface CrmIntroPathRecord {
  id: string;
  target_person_id: string;
  hop_count: number;
  path_strength: number;
  confidence_score: number;
  labels: string[];
}

export interface CrmMergeSuggestionRecord {
  id: string;
  left_contact_id?: string | null;
  right_contact_id?: string | null;
  left_label: string;
  right_label: string;
  match_confidence: number;
  reasons: string[];
  status: 'pending' | 'approved' | 'rejected';
}

export interface CrmSegmentRecord {
  id: string;
  name: string;
  description?: string;
  contact_count: number;
  average_fit_score: number;
  next_action_label: string;
  status: 'active' | 'saved' | 'dynamic' | 'archived';
  rules: string[];
}
