export type IterationScope = 'whole_deck' | 'selected_slides' | 'new_slides_only' | 'appendix' | string;

export type IterationStatus = 'draft' | 'ready_for_review' | 'accepted' | 'compiled' | 'failed' | string;

export interface DeckIterationSummary {
  id: string;
  deckId: string;
  iterationNumber: number;
  label: string;
  scope: IterationScope;
  slideCount: number;
  status: IterationStatus;
  createdAt: string;
  updatedAt: string;
  batchId: string;
}

export interface DeckIterationsResponse {
  deckId: string;
  activeIterationId: string | null;
  iterations: DeckIterationSummary[];
}
