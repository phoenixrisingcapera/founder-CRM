export interface SessionResponse {
  user: { id: string; email: string; full_name: string };
  workspace: {
    id: string; name: string; slug: string;
    active_raise_name?: string | null;
    active_project_id?: string | null;
    active_project_title?: string | null;
    active_goal_type?: string | null;
  };
}

export interface AuthPayload {
  full_name?: string;
  email: string;
  password: string;
}

export interface DashboardSummary {
  workspace_name: string;
  active_raise_name?: string | null;
  active_project_id?: string | null;
  active_project_title?: string | null;
  active_goal_type?: string | null;
  metrics: { label: string; value: number; tone: string }[];
  upcoming_follow_ups: string[];
  suggested_actions: ActionRecord[];
  deck_readiness_score: number;
  feature_flags: { exports_enabled: boolean };
  latest_goal_score?: number | null;
  latest_goal_score_label?: string | null;
  latest_ai_artifact_id?: string | null;
  latest_ai_artifact_title?: string | null;
}

export interface PersonRecord {
  id: string;
  name: string;
  email?: string | null;
  company?: string | null;
  role?: string | null;
  relationship_status: string;
  notes?: string | null;
  source_kind: string;
  last_contact_at?: string | null;
  next_follow_up_at?: string | null;
  created_at?: string | null;
}

export interface ContactRecord {
  id: string;
  person_id?: string | null;
  name: string;
  email?: string | null;
  company?: string | null;
  role?: string | null;
  contact_type: string;
  relationship_status: string;
  notes?: string | null;
}

export interface InvestorRecord {
  id: string;
  person_id?: string | null;
  name: string;
  investor_type: string;
  preferred_stage?: string | null;
  sector_relevance?: string | null;
  thesis?: string | null;
  check_fit_notes?: string | null;
  warm_intro_path?: string | null;
  risk_flags?: string | null;
  pipeline_stage: string;
}

export interface AudienceProfile {
  id: string;
  code: string;
  label: string;
  description: string;
}

export interface DeckSlide {
  id: string;
  slide_order: number;
  title: string;
  content: string;
}

export interface DeckRecord {
  id: string;
  title: string;
  audience?: string | null;
  status: string;
  source_file_name?: string | null;
  slides: DeckSlide[];
}

export interface ArtifactRecord {
  id: string;
  deck_id: string;
  generation_run_id: string;
  artifact_type: string;
  artifact_status: string;
  title: string;
  content_markdown: string;
  export_enabled: boolean;
  created_at: string;
}

export interface DeckGenerationRunRecord {
  id: string;
  deck_id: string;
  deck_title?: string | null;
  audience_profile_id?: string | null;
  audience_label?: string | null;
  provider: string;
  model: string;
  status: string;
  prompt_summary: string;
  created_at: string;
  artifacts: ArtifactRecord[];
  telemetry_event_count: number;
}

export interface ArtifactDetailRecord extends ArtifactRecord {
  deck_title?: string | null;
  audience_label?: string | null;
  run?: DeckGenerationRunRecord | null;
}

export interface PipelineDealRecord {
  id: string;
  name: string;
  stage: string;
  status: string;
  target_raise_amount?: string | null;
  notes?: string | null;
  person_id?: string | null;
  person_name?: string | null;
}

export interface CompanyRecord {
  id: string;
  name: string;
  website?: string | null;
  company_type: string;
  sector?: string | null;
  geography?: string | null;
  relationship_summary?: string | null;
}

export interface ProjectRecord {
  id: string;
  title: string;
  goal_type: string;
  status: string;
  summary?: string | null;
}

export interface DispatchRecord {
  id: string;
  title: string;
  project_id?: string | null;
  person_id?: string | null;
  intro_path_id?: string | null;
  channel: string;
  status: string;
  next_step?: string | null;
  project_title?: string | null;
  person_name?: string | null;
  intro_path_label?: string | null;
}

export interface WarmPathRecord {
  intermediary_person_id: string;
  intermediary_name: string;
  intermediary_relationship_status?: string | null;
  target_person_id: string;
  target_name: string;
  confidence: string;
  path_label: string;
  relationship_type: string;
  intro_path_id?: string | null;
}

export interface ActionRecord {
  person_id: string;
  person_name: string;
  organization?: string | null;
  total_score: number;
  reasons: string[];
  days_since_last_contact?: number | null;
  suggested_action: string;
  intro_paths_available: number;
}

export interface OpportunityRecord {
  id: string;
  title: string;
  company_id?: string | null;
  person_id?: string | null;
  opportunity_type: string;
  status: string;
  value_label?: string | null;
  notes?: string | null;
  company_name?: string | null;
  person_name?: string | null;
}

export interface RelationshipScoreRecord {
  person_id: string;
  person_name: string;
  organization?: string | null;
  goal_type: string;
  fit_score: number;
  proximity_score: number;
  total_score: number;
  reasons: string[];
}

export interface GoalScoreRecord {
  id: string;
  project_id: string;
  person_id?: string | null;
  company_id?: string | null;
  opportunity_id?: string | null;
  project_title?: string | null;
  person_name?: string | null;
  company_name?: string | null;
  opportunity_title?: string | null;
  total_score: number;
  relationship_strength_score: number;
  warm_path_score: number;
  sector_fit_score: number;
  stage_fit_score: number;
  recency_score: number;
  confidence_score: number;
  reasons: string[];
  missing_data: string[];
  recommended_next_action: string;
  created_at?: string | null;
}

export interface AiArtifactRecord {
  id: string;
  project_id: string;
  person_id?: string | null;
  company_id?: string | null;
  opportunity_id?: string | null;
  goal_score_id?: string | null;
  artifact_type: string;
  title: string;
  content_markdown: string;
  project_title?: string | null;
  person_name?: string | null;
  company_name?: string | null;
  opportunity_title?: string | null;
  created_at?: string | null;
}

export interface RelationshipGraphNode {
  id: string;
  label: string;
  kind: string;
}

export interface RelationshipGraphEdge {
  source: string;
  target: string;
  label: string;
}

export interface RelationshipGraphRecord {
  nodes: RelationshipGraphNode[];
  edges: RelationshipGraphEdge[];
}

export interface InteractionNoteRecord {
  id: string;
  title: string;
  body: string;
  person_id?: string | null;
  created_at: string;
}

export interface FollowUpTaskRecord {
  id: string;
  title: string;
  status: string;
  due_at?: string | null;
  person_id?: string | null;
}

export interface SettingsSummary {
  exports_enabled: boolean;
  api_keys: { provider: string; configured: boolean }[];
}

export interface AdminMetric {
  label: string;
  value: number | string;
}

export interface AdminOverview {
  summary: AdminMetric[];
  recent_failures: number;
  recent_ai_runs: number;
  recent_artifacts: number;
}

export interface AdminTelemetryEvent {
  id: string;
  event_name: string;
  event_level: string;
  status?: string | null;
  provider?: string | null;
  model?: string | null;
  latency_ms?: number | null;
  request_id?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface AdminTelemetryEvents {
  total: number;
  failed: number;
  events: AdminTelemetryEvent[];
}

export interface AdminFailureTicket {
  id: string;
  route?: string | null;
  api_path?: string | null;
  status_code?: number | null;
  severity: string;
  source: string;
  error_name?: string | null;
  error_message: string;
  request_id?: string | null;
  created_at: string;
}

export interface AdminFailureTickets {
  total: number;
  tickets: AdminFailureTicket[];
}

export interface AdminProviderHealth {
  providers: { provider: string; configured: boolean; source: string }[];
}

export interface AdminRun {
  id: string;
  deck_id: string;
  provider: string;
  model: string;
  status: string;
  prompt_summary: string;
  created_at: string;
}

export interface AdminRuns {
  total: number;
  runs: AdminRun[];
}
