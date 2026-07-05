export interface DashboardUserSummary {
  id: string;
  handle: string;
  role: string;
  plan: string;
}

export interface DashboardDeckSummary {
  id: string;
  title: string;
  description: string;
  audience: string;
  purpose: string;
  status: 'uploaded' | 'preparing' | 'ready_to_review' | 'reviewed' | 'exported';
  slideCount: number;
  thumbnailUrl: string | null;
  updatedAt: string;
}

export interface DashboardSlidePreview {
  id: string;
  deckId: string;
  slideNumber: number;
  title: string;
  thumbnailUrl: string | null;
  previewImageUrl: string | null;
  status: 'original' | 'edited' | 'accepted';
  updatedAt: string;
}

export interface DashboardIterationSummary {
  id: string;
  deckId: string;
  deckTitle: string;
  iterationNumber: number;
  title: string;
  scope: 'whole_deck' | 'selected_slides';
  status: 'draft' | 'ready_for_review' | 'accepted' | 'compiled' | 'failed';
  thumbnailUrl: string | null;
  updatedAt: string;
}

export interface DashboardStats {
  uploadedDecks: number;
  iterationsThisWeek: number;
  slidesInLibrary: number;
  teamMembers: number;
}

export interface WorkspaceDashboardResponse {
  user: DashboardUserSummary;
  stats: DashboardStats;
  latestDeck: DashboardDeckSummary | null;
  decks: DashboardDeckSummary[];
  recentSlides: DashboardSlidePreview[];
  latestIterations: DashboardIterationSummary[];
}
