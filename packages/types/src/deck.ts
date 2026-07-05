export interface DeckSectionRecord {
  id: string;
  organisation_id: string;
  deck_id: string;
  title: string;
  sort_order: number;
  body_markdown?: string | null;
}

export interface DeckSlideRecord {
  id: string;
  organisation_id: string;
  deck_id: string;
  section_order: number;
  slide_order: number;
  title: string;
  body_markdown: string;
}

export interface DeckShareLinkRecord {
  id: string;
  organisation_id: string;
  deck_id: string;
  token: string;
  visibility: string;
  expires_at?: string | null;
}

export interface DeckRecord {
  id: string;
  created_at?: string;
  updated_at?: string;
  organisation_id?: string;
  created_by?: string;
  project_id?: string | null;
  company_id?: string | null;
  deal_id?: string | null;
  title: string;
  status: string;
  summary?: string | null;
  sections: DeckSectionRecord[];
  slides: DeckSlideRecord[];
  share_links: DeckShareLinkRecord[];
}

export interface DeckAssistantSlideRecommendationRecord {
  slide_id: string;
  slide_title: string;
  recommendation: string;
  rationale: string;
}

export interface DeckAssistantResponseRecord {
  deck_id: string;
  mode: string;
  scope: string;
  iteration_brief: string;
  context_summary: string;
  recommendations: DeckAssistantSlideRecommendationRecord[];
  next_actions: string[];
}
