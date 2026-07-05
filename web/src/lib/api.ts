import type {
    AiArtifactRecord,
    ActionRecord,
    AdminFailureTickets,
    AdminOverview,
    AdminProviderHealth,
    AdminRuns,
    AdminTelemetryEvents,
  ArtifactRecord,
  ArtifactDetailRecord,
  AudienceProfile,
  AuthPayload,
  CompanyRecord,
  ContactRecord,
  DashboardSummary,
  DeckRecord,
  DeckGenerationRunRecord,
  DispatchRecord,
  FollowUpTaskRecord,
  InteractionNoteRecord,
  InvestorRecord,
    OpportunityRecord,
    PersonRecord,
  PipelineDealRecord,
  ProjectRecord,
    RelationshipGraphRecord,
    GoalScoreRecord,
    RelationshipScoreRecord,
  SessionResponse,
  SettingsSummary,
  WarmPathRecord,
} from '$lib/types';

const apiBaseUrl = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8010/api';

let sessionPromise: Promise<SessionResponse> | null = null;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: 'include',
    ...init
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: `Request failed: ${response.status}` }));
    throw new Error(payload.detail || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function ensureSession(): Promise<SessionResponse> {
  if (!sessionPromise) {
    sessionPromise = request<SessionResponse>('/auth/me');
  }

  return sessionPromise;
}

export function clearSessionCache() {
  sessionPromise = null;
}

export async function signUp(payload: AuthPayload) {
  const session = await request<SessionResponse>('/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  sessionPromise = Promise.resolve(session);
  return session;
}

export async function signIn(payload: AuthPayload) {
  const session = await request<SessionResponse>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: payload.email, password: payload.password })
  });
  sessionPromise = Promise.resolve(session);
  return session;
}

export async function signOut() {
  await request<{ status: string }>('/auth/logout', { method: 'POST' });
  clearSessionCache();
}

export async function createDemoSession() {
  const session = await request<SessionResponse>('/auth/demo-session', { method: 'POST' });
  sessionPromise = Promise.resolve(session);
  return session;
}

export const getDashboard = () => request<DashboardSummary>('/dashboard');
export const listContacts = () => request<ContactRecord[]>('/contacts');
export const listCompanies = () => request<CompanyRecord[]>('/companies');
export const listInvestors = () => request<InvestorRecord[]>('/investors');
export const listAudiences = () => request<AudienceProfile[]>('/audiences');
export const listDecks = () => request<DeckRecord[]>('/decks');
export const listArtifacts = () => request<ArtifactRecord[]>('/artifacts');
export const getArtifact = (artifactId: string) => request<ArtifactDetailRecord>(`/artifacts/${artifactId}`);
export const listGenerationRuns = (deckId: string) => request<DeckGenerationRunRecord[]>(`/decks/${deckId}/generation-runs`);
export const getGenerationRun = (runId: string) => request<DeckGenerationRunRecord>(`/generation-runs/${runId}`);
export const listPipelineDeals = () => request<PipelineDealRecord[]>('/pipeline-deals');
export const listPeople = () => request<PersonRecord[]>('/people');
export const createPerson = (payload: Partial<PersonRecord>) =>
  request<PersonRecord>('/people', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  });
export const updatePerson = (personId: string, payload: Partial<PersonRecord>) =>
  request<PersonRecord>(`/people/${personId}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  });
export const deletePerson = (personId: string) =>
  request<{ status: string }>(`/people/${personId}`, { method: 'DELETE' });
export const listProjects = () => request<ProjectRecord[]>('/projects');
export const activateProject = (projectId: string) =>
  request<{ status: string; project_id: string; project_title: string }>(`/projects/${projectId}/activate`, { method: 'POST' });
export const deactivateProject = () =>
  request<{ status: string }>('/projects/deactivate', { method: 'POST' });
export const listDispatches = () => request<DispatchRecord[]>('/dispatches');
export const listOpportunities = () => request<OpportunityRecord[]>('/opportunities');
export const findWarmPaths = (targetPersonId: string) =>
  request<WarmPathRecord[]>(`/warm-paths?target_person_id=${encodeURIComponent(targetPersonId)}`);
export const getActionQueue = (goalType = 'raise_funding') =>
  request<ActionRecord[]>(`/action-queue?goal_type=${encodeURIComponent(goalType)}`);
export const getRelationshipFit = (goalType: string) => request<RelationshipScoreRecord[]>(`/relationship-fit?goal_type=${encodeURIComponent(goalType)}`);
export const getRelationshipGraph = () => request<RelationshipGraphRecord>('/relationship-graph');
export const listGoalScores = () => request<GoalScoreRecord[]>('/goal-scores');
export const createGoalScore = (payload: { project_id: string; person_id?: string; company_id?: string; opportunity_id?: string }) =>
  request<GoalScoreRecord>('/goal-scores', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  });
export const listAiArtifacts = () => request<AiArtifactRecord[]>('/ai-artifacts');
export const getAiArtifact = (artifactId: string) => request<AiArtifactRecord>(`/ai-artifacts/${artifactId}`);
export const generateAiArtifact = (payload: {
  goal_score_id: string;
  project_id: string;
  person_id?: string;
  company_id?: string;
  opportunity_id?: string;
  instruction?: string;
  api_key?: string;
  provider?: string;
}) => request<AiArtifactRecord>('/ai-artifacts/generate', {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
});
export const listNotes = () => request<InteractionNoteRecord[]>('/notes');
export const listTasks = () => request<FollowUpTaskRecord[]>('/tasks');
export const getSettings = () => request<SettingsSummary>('/settings');
export const getAdminOverview = () => request<AdminOverview>('/admin/overview');
export const getAdminTelemetryEvents = () => request<AdminTelemetryEvents>('/admin/telemetry/events');
export const getAdminFailureTickets = () => request<AdminFailureTickets>('/admin/failure-tickets');
export const getAdminProviderHealth = () => request<AdminProviderHealth>('/admin/provider-health');
export const getAdminRuns = () => request<AdminRuns>('/admin/runs');

export const reportFailureTicket = (payload: {
  route?: string | null;
  page_url?: string | null;
  api_path?: string | null;
  status_code?: number | null;
  error_name?: string | null;
  error_message: string;
  error_stack?: string | null;
  severity?: string;
  source?: string;
  request_id?: string | null;
  context?: Record<string, unknown>;
}) =>
  request('/admin/failure-tickets/report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

export const createContact = (payload: Partial<ContactRecord>) =>
  request<ContactRecord>('/contacts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

export const updateContact = (contactId: string, payload: Partial<ContactRecord>) =>
  request<ContactRecord>(`/contacts/${contactId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

export const deleteContact = (contactId: string) =>
  request<{ status: string }>(`/contacts/${contactId}`, { method: 'DELETE' });

export const createInvestor = (payload: Partial<InvestorRecord>) =>
  request<InvestorRecord>('/investors', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

export const updateInvestor = (investorId: string, payload: Partial<InvestorRecord>) =>
  request<InvestorRecord>(`/investors/${investorId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

export const deleteInvestor = (investorId: string) =>
  request<{ status: string }>(`/investors/${investorId}`, { method: 'DELETE' });

export const createCompany = (payload: Partial<CompanyRecord>) =>
  request<CompanyRecord>('/companies', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  });

export const updateCompany = (companyId: string, payload: Partial<CompanyRecord>) =>
  request<CompanyRecord>(`/companies/${companyId}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  });

export const deleteCompany = (companyId: string) => request<{ status: string }>(`/companies/${companyId}`, { method: 'DELETE' });

export const createProject = (payload: Partial<ProjectRecord>) =>
  request<ProjectRecord>('/projects', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  });

export const createDispatch = (payload: Partial<DispatchRecord>) =>
  request<DispatchRecord>('/dispatches', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  });

export const createOpportunity = (payload: Partial<OpportunityRecord>) =>
  request<OpportunityRecord>('/opportunities', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  });

export const createPipelineDeal = (payload: Partial<PipelineDealRecord>) =>
  request<PipelineDealRecord>('/pipeline-deals', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

export const updatePipelineDeal = (dealId: string, payload: Partial<PipelineDealRecord>) =>
  request<PipelineDealRecord>(`/pipeline-deals/${dealId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

export const deletePipelineDeal = (dealId: string) =>
  request<{ status: string }>(`/pipeline-deals/${dealId}`, { method: 'DELETE' });

export const createNote = (payload: Partial<InteractionNoteRecord>) =>
  request<InteractionNoteRecord>('/notes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

export const updateNote = (noteId: string, payload: Partial<InteractionNoteRecord>) =>
  request<InteractionNoteRecord>(`/notes/${noteId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

export const deleteNote = (noteId: string) => request<{ status: string }>(`/notes/${noteId}`, { method: 'DELETE' });

export const createTask = (payload: Partial<FollowUpTaskRecord>) =>
  request<FollowUpTaskRecord>('/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

export const updateTask = (taskId: string, payload: Partial<FollowUpTaskRecord>) =>
  request<FollowUpTaskRecord>(`/tasks/${taskId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

export const deleteTask = (taskId: string) => request<{ status: string }>(`/tasks/${taskId}`, { method: 'DELETE' });

export async function uploadDeck(payload: { title: string; audience: string; file: File }) {
  const formData = new FormData();
  formData.set('title', payload.title);
  formData.set('audience', payload.audience);
  formData.set('file', payload.file);
  return request<DeckRecord>('/decks/upload', { method: 'POST', body: formData });
}

export async function createGenerationRun(
  deckId: string,
  payload: { audience_code: string; instruction: string; api_key?: string; provider?: string }
) {
  return request<{ run_id: string; artifact: ArtifactRecord }>(`/decks/${deckId}/generation-runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

export async function saveApiKey(payload: { provider: string; api_key: string }) {
  return request<SettingsSummary>('/settings/api-keys', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

export async function createArtifactSignedUrl(artifactId: string) {
  return request<{ artifact_id: string; download_url: string }>(`/artifacts/${artifactId}/signed-url`, {
    method: 'POST'
  });
}

export const updateArtifactStatus = (artifactId: string, status: string) =>
  request<ArtifactDetailRecord>(`/artifacts/${artifactId}/status?status=${encodeURIComponent(status)}`, {
    method: 'PATCH'
  });

export const deleteArtifact = (artifactId: string) => request<{ status: string }>(`/artifacts/${artifactId}`, { method: 'DELETE' });
