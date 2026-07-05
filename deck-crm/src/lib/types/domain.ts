export const suggestionStatuses = ['pending', 'accepted', 'rejected', 'edited', 'applied'] as const;
export const billingIntervals = ['monthly', 'annual'] as const;
export const workspaceSubscriptionStatuses = ['trialing', 'active', 'past_due', 'canceled'] as const;
export const billingInvoiceStatuses = ['draft', 'open', 'paid', 'void'] as const;
export const connectedAccountProviders = ['microsoft', 'linkedin'] as const;
export const connectedAccountStatuses = ['connected', 'needs_reauth', 'disconnected', 'syncing'] as const;

export type DeckStatus =
  | 'uploaded'
  | 'extracting'
  | 'extraction_failed'
  | 'parsing'
  | 'structuring'
  | 'extracting_blocks'
  | 'classifying_blocks'
  | 'analysing'
  | 'adapting'
  | 'reviewed'
  | 'ready'
  | 'failed';
export type SuggestionStatus = (typeof suggestionStatuses)[number];
export type BillingInterval = (typeof billingIntervals)[number];
export type WorkspaceSubscriptionStatus = (typeof workspaceSubscriptionStatuses)[number];
export type BillingInvoiceStatus = (typeof billingInvoiceStatuses)[number];
export type ConnectedAccountProvider = (typeof connectedAccountProviders)[number];
export type ConnectedAccountStatus = (typeof connectedAccountStatuses)[number];

export interface User {
  id: string;
  email: string;
  name: string;
}

export interface Workspace {
  id: string;
  name: string;
  userId: string;
}

export interface AudienceProfile {
  id: string;
  label: string;
  focus: string[];
  tone: string;
}

export interface DeckFile {
  id: string;
  filename: string;
  mimeType: string;
  size: number;
  uploadedAt: string;
}

export interface Deck {
  id: string;
  workspaceId: string;
  title: string;
  audience: string;
  purpose: string;
  status: DeckStatus;
  createdAt: string;
  updatedAt: string;
  summary: string;
  file?: DeckFile;
  thumbnailUrl?: string | null;
  previewUrl?: string | null;
  firstSlideId?: string | null;
  originalFilename?: string | null;
}

export interface DeckSlide {
  id: string;
  deckId: string;
  slideIndex: number;
  slideNumber?: number;
  title: string;
  role: string;
  rawText: string;
  extractedText?: string;
  narrativeNotes: string;
  status?: 'ready' | 'pending' | string;
  previewUrl?: string | null;
  previewImageUrl?: string | null;
  thumbnailUrl?: string | null;
  previewWidth?: number | null;
  previewHeight?: number | null;
  previewMimeType?: string | null;
}

export interface DeckSlideBlock {
  id: string;
  slideId: string;
  blockIndex: number;
  rawText: string;
  normalizedText: string;
  blockType: 'headline' | 'body' | 'metric' | 'quote' | 'bullet';
  position?: string;
  style?: string;
}

export interface BlockClassification {
  id: string;
  blockId: string;
  semanticTag: string;
  diligenceCategory: string;
  confidence: number;
}

export interface AnalysisRun {
  id: string;
  deckId: string;
  status: 'queued' | 'running' | 'completed';
  createdAt: string;
}

export interface AnalysisFinding {
  id: string;
  deckId: string;
  slideId: string;
  blockId?: string;
  title: string;
  detail: string;
  severity: 'high' | 'medium' | 'low';
  category: string;
}

export interface AdaptationRun {
  id: string;
  deckId: string;
  audience: string;
  purpose: string;
  createdAt: string;
}

export interface AdaptationSuggestion {
  id: string;
  deckId: string;
  slideId: string;
  blockId?: string;
  title: string;
  reason: string;
  suggestedText: string;
  status: SuggestionStatus;
  audience: string;
}

export interface SmartEditRun {
  id: string;
  deckId: string;
  slideId: string;
  blockId: string;
  instruction: string;
  createdAt: string;
}

export interface SmartEditSuggestion {
  id: string;
  runId: string;
  deckId: string;
  slideId: string;
  blockId: string;
  originalText: string;
  suggestedText: string;
  reason: string;
  riskLevel: 'low' | 'medium' | 'high';
  status: SuggestionStatus;
}

export interface DeckSlideRevision {
  id: string;
  deckId: string;
  slideId: string;
  blockId: string;
  previousText: string;
  nextText: string;
  reason: string;
  createdAt: string;
}

export interface DeckExport {
  id: string;
  deckId: string;
  type: 'diligence_report' | 'adapted_outline' | 'final_deck' | string;
  content: string;
  createdAt: string;
  downloadUrl?: string;
}

export interface DeckGraph {
  deck: Deck;
  slides: DeckSlide[];
  blocks: DeckSlideBlock[];
  classifications: BlockClassification[];
  findings: AnalysisFinding[];
  suggestions: AdaptationSuggestion[];
  smartEditSuggestions: SmartEditSuggestion[];
  revisions: DeckSlideRevision[];
}

export interface BillingPlan {
  id: string;
  code: string;
  name: string;
  description: string;
  monthlyPriceCents: number | null;
  annualPriceCents: number | null;
  ctaLabel: string;
  isHighlighted: boolean;
  isEnterprise: boolean;
  seatLabel: string | null;
  featureBullets: string[];
}

export interface WorkspaceSubscription {
  id: string;
  workspaceId: string;
  billingPlanId: string;
  status: WorkspaceSubscriptionStatus;
  interval: BillingInterval;
  seatCount: number;
  cancelAtPeriodEnd: boolean;
  currentPeriodStart: string;
  currentPeriodEnd: string;
}

export interface BillingInvoice {
  id: string;
  invoiceNumber: string;
  status: BillingInvoiceStatus;
  amountCents: number;
  currency: string;
  issuedAt: string;
  paidAt: string | null;
}

export interface BillingWorkspaceSnapshot {
  workspace: {
    id: string;
    name: string;
  };
  plans: BillingPlan[];
  currentPlan: BillingPlan | null;
  subscription: WorkspaceSubscription | null;
  invoices: BillingInvoice[];
}

export interface UserConnectedAccount {
  id: string;
  provider: ConnectedAccountProvider;
  status: ConnectedAccountStatus;
  externalAccountId: string | null;
  externalEmail: string | null;
  externalDisplayName: string | null;
  externalProfileUrl: string | null;
  scopes: string[];
  accessTokenMasked: string | null;
  refreshTokenStored: boolean;
  lastSyncedAt: string | null;
  syncMetadataJson: Record<string, unknown> | null;
}

export interface UserProfileSnapshot {
  id: string;
  userId: string;
  displayName: string | null;
  headline: string | null;
  companyName: string | null;
  jobTitle: string | null;
  department: string | null;
  city: string | null;
  region: string | null;
  country: string | null;
  timezone: string | null;
  preferredLanguage: string | null;
  photoUrl: string | null;
  bio: string | null;
  linkedinProfileUrl: string | null;
  microsoftTenantId: string | null;
  workEmail: string | null;
  mobilePhone: string | null;
  skillsJson: unknown;
  educationJson: unknown;
  certificationsJson: unknown;
  profileSourceJson: Record<string, unknown> | null;
}

export interface UserSettingsSnapshot {
  user: {
    id: string;
    email: string;
    name: string;
  };
  profile: UserProfileSnapshot | null;
  connectedAccounts: UserConnectedAccount[];
}

export interface ConnectUserAccountRequest {
  provider: ConnectedAccountProvider;
  origin?: 'settings_page' | 'connected_accounts_page' | 'reminder_popup';
}
