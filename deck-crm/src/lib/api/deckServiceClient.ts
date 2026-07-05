import { readApiJsonOrThrow } from './apiError';
import { deckProductApiPath } from '$lib/contracts';
import type {
  FirstDeckUploadRouteResponse,
  WorkspaceAiProviderRouteResponse,
  WorkspaceAiProviderSaveRequest,
  WorkspaceAiProviderSaveRouteResponse,
  WorkspaceSummaryRouteResponse
} from '$lib/contracts';

type DeckUploadStage = 'creating' | 'requesting_upload' | 'uploading' | 'confirming' | 'processing' | 'ready';

type InspectionResponse = {
  enabled: boolean;
  active: boolean;
  founderEmail: string | null;
  hasPassword: boolean;
  backendConfigured: boolean;
  bypasses: {
    routeAccess: boolean;
    billing: boolean;
    providers: boolean;
  };
};

type SessionValidationResponse = {
  valid: boolean;
  inspection?: InspectionResponse;
};

type SignInRequest = {
  email: string;
  password: string;
};

type SignUpRequest = {
  name: string;
  email: string;
  password: string;
  companyName?: string;
  role?: 'general' | 'user';
  acceptedTerms: boolean;
};

type AuthRouteResponse = {
  nextUrl: string;
  user: {
    id: string;
    email: string;
    name: string;
    role: 'super_admin' | 'admin' | 'user' | 'general';
  };
  workspace?: {
    id: string;
    name: string;
  };
};

type PublicInterestPayload = {
  email: string;
  name?: string;
  company_name?: string;
  company_website_url?: string;
  role_label?: string;
  use_case?: string;
  message?: string;
  source_page?: string;
  turnstileToken?: string;
};

type PublicInterestResponse = {
  ok: true;
  lead_id: string;
  message: string;
};

type CurrentUserResponse = {
  user: {
    id: string;
    email: string;
    name: string;
    role: 'super_admin' | 'admin' | 'user';
    preferredTheme: 'light' | 'dark';
    billingPlan: string;
    permissions: string[];
    founderInspectionMode?: boolean;
  };
  inspection?: SessionValidationResponse['inspection'];
};

type BillingStateResponse = {
  plan: string;
  status?: string;
};

type DeckUploadIntake = {
  companyName?: string;
  websiteUrl?: string;
  audience?: string;
  purpose?: string;
  founderName?: string;
  notes?: string;
  teamNotes?: string;
  linkedinUrls?: string[];
  supportingUrls?: string[];
};

type DeckUploadCompleteResponse = {
  deckId?: string;
};

type DeckUploadFlowOptions = {
  onStage?: (stage: DeckUploadStage) => void;
};

function buildUrl(path: string) {
  if (path.startsWith('/api/')) {
    return path;
  }

  return `/api${path}`;
}

function networkFailureMessage(method: string, path: string, err: unknown) {
  const detail = err instanceof Error && err.message ? ` ${err.message}` : '';
  return `${method} ${path} failed before a response was received.${detail}`;
}

async function deckServiceApiGet<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path), {
      credentials: 'include'
    });
  } catch (err) {
    throw new Error(networkFailureMessage('GET', path, err));
  }

  return readApiJsonOrThrow<T>(response, `GET ${path} failed`, path);
}

async function deckServiceApiPost<T>(path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path), {
      method: 'POST',
      credentials: 'include',
      headers: body ? { 'content-type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined
    });
  } catch (err) {
    throw new Error(networkFailureMessage('POST', path, err));
  }

  return readApiJsonOrThrow<T>(response, `POST ${path} failed`, path);
}

function createUploadRequestId() {
  return typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? `upload-${crypto.randomUUID()}`
    : `upload-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function uploadDeckViaProductRoute(
  file: File,
  intake?: DeckUploadIntake,
  requestId: string = createUploadRequestId()
): Promise<DeckUploadCompleteResponse> {
  const formData = new FormData();
  formData.set('deck', file);
  formData.set('audience', intake?.audience?.trim() || 'Investment Committee');
  formData.set('purpose', intake?.purpose?.trim() || 'Initial diligence review');
  if (intake?.companyName?.trim()) formData.set('company_name', intake.companyName.trim());
  if (intake?.websiteUrl?.trim()) formData.set('website_url', intake.websiteUrl.trim());
  if (intake?.founderName?.trim()) formData.set('founder_name', intake.founderName.trim());
  if (intake?.notes?.trim()) formData.set('notes', intake.notes.trim());
  if (intake?.teamNotes?.trim()) formData.set('team_notes', intake.teamNotes.trim());
  if (intake?.linkedinUrls?.length) {
    formData.set('linkedin_urls', intake.linkedinUrls.map((url) => url.trim()).filter(Boolean).join('\n'));
  }
  if (intake?.supportingUrls?.length) {
    formData.set('supporting_urls', intake.supportingUrls.map((url) => url.trim()).filter(Boolean).join('\n'));
  }

  const response = await fetch(deckProductApiPath('/decks/upload'), {
    method: 'POST',
    credentials: 'include',
    headers: {
      'x-request-id': requestId
    },
    body: formData
  });

  return readApiJsonOrThrow<DeckUploadCompleteResponse>(response, 'Deck upload failed.', deckProductApiPath('/decks/upload'));
}

async function uploadFirstDeckViaBridge(file: File, payload?: unknown, options: DeckUploadFlowOptions = {}): Promise<FirstDeckUploadRouteResponse> {
  const intake = payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : {};
  const requestId = createUploadRequestId();

  options.onStage?.('uploading');
  const confirmation = await uploadDeckViaProductRoute(
    file,
    {
      companyName: typeof intake.companyName === 'string' ? intake.companyName : undefined,
      websiteUrl: typeof intake.websiteUrl === 'string' ? intake.websiteUrl : undefined,
      audience: typeof intake.audience === 'string' ? intake.audience : undefined,
      purpose: typeof intake.purpose === 'string' ? intake.purpose : undefined,
      founderName: typeof intake.founderName === 'string' ? intake.founderName : undefined,
      notes: typeof intake.notes === 'string' ? intake.notes : undefined,
      teamNotes: typeof intake.teamNotes === 'string' ? intake.teamNotes : undefined,
      linkedinUrls: Array.isArray(intake.linkedinUrls)
        ? intake.linkedinUrls.filter((value): value is string => typeof value === 'string')
        : [],
      supportingUrls: Array.isArray(intake.supportingUrls)
        ? intake.supportingUrls.filter((value): value is string => typeof value === 'string')
        : []
    },
    requestId
  );
  const deckId = String(confirmation.deckId ?? '');
  if (!deckId) {
    throw new Error('Deck upload finished without a persisted deck id.');
  }

  options.onStage?.('ready');
  return {
    ok: true,
    deckId,
    filename: file.name,
    confirmation: null,
    workspace: (await deckServiceApiGet<WorkspaceSummaryRouteResponse>(deckProductApiPath('/workspace-summary'))).workspace
  };
}

async function getWorkspaceAiProviderViaBridge(): Promise<WorkspaceAiProviderRouteResponse> {
  const response = await fetch('/api/settings/workspace/ai-provider', {
    credentials: 'include'
  });
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      typeof payload?.message === 'string'
        ? payload.message
        : 'Could not load workspace AI configuration.'
    );
  }

  return payload as WorkspaceAiProviderRouteResponse;
}

async function saveWorkspaceAiProviderViaBridge(
  payload: WorkspaceAiProviderSaveRequest
): Promise<WorkspaceAiProviderSaveRouteResponse> {
  const response = await fetch('/api/settings/workspace/ai-provider', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'content-type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  const result = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      typeof result?.message === 'string'
        ? result.message
        : 'Could not save workspace AI configuration.'
    );
  }

  return result as WorkspaceAiProviderSaveRouteResponse;
}

export const deckServiceClient = {
  validateSession: () => deckServiceApiGet<SessionValidationResponse>('/auth/session/validate'),
  signIn: (payload: SignInRequest) => deckServiceApiPost<AuthRouteResponse>('/auth/sign-in', payload),
  signUp: (payload: SignUpRequest) => deckServiceApiPost<AuthRouteResponse>('/auth/sign-up', payload),
  completeAuthCallback: (payload: Partial<SignUpRequest & SignInRequest>) =>
    deckServiceApiPost<{ status: 'ok'; nextUrl: string }>('/auth/callback', payload),
  getCurrentUser: () => deckServiceApiGet<CurrentUserResponse>('/me'),
  getBillingState: () => deckServiceApiGet<BillingStateResponse>('/billing/me'),
  getWorkspaceSummary: () => deckServiceApiGet<WorkspaceSummaryRouteResponse>(deckProductApiPath('/workspace-summary')),
  uploadFirstDeck: (file: File, payload?: unknown, options?: DeckUploadFlowOptions): Promise<FirstDeckUploadRouteResponse> =>
    uploadFirstDeckViaBridge(file, payload, options),
  getWorkspaceAiProvider: () => getWorkspaceAiProviderViaBridge(),
  saveWorkspaceAiProvider: (payload: WorkspaceAiProviderSaveRequest) => saveWorkspaceAiProviderViaBridge(payload),
  submitPublicInterest: (payload: PublicInterestPayload) =>
    deckServiceApiPost<PublicInterestResponse>('/public/interest', payload)
};
