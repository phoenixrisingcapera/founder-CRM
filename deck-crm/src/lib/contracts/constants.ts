const DEFAULT_DECK_PRODUCT_SLUG = 'deck-aistack-codes';

function readDeckProductSlug() {
  const value = import.meta.env.PUBLIC_DECK_PRODUCT_SLUG;
  if (typeof value === 'string' && value.trim()) {
    return value.trim();
  }
  return DEFAULT_DECK_PRODUCT_SLUG;
}

export const DECK_PRODUCT_SLUG = readDeckProductSlug();
export const DECK_PRODUCT_ROUTE_PREFIX = `/products/${DECK_PRODUCT_SLUG}`;
export const DECK_PRODUCT_API_PREFIX = `/api/products/${DECK_PRODUCT_SLUG}`;

function normalizeProductPath(path: string) {
  if (!path) {
    return '';
  }

  return path.startsWith('/') ? path : `/${path}`;
}

export function deckProductRoutePath(path = '') {
  return `${DECK_PRODUCT_ROUTE_PREFIX}${normalizeProductPath(path)}`;
}

export function deckProductApiPath(path = '') {
  return `${DECK_PRODUCT_API_PREFIX}${normalizeProductPath(path)}`;
}

export function deckWorkflowStateApiPath(deckId: string) {
  return deckProductApiPath(`/decks/${deckId}/workflow-state`);
}

export function deckSmartDeckReadinessApiPath(deckId: string) {
  return deckProductApiPath(`/decks/${deckId}/smart-deck-readiness`);
}

export function deckWorkflowJobApiPath(jobId: string) {
  return `/api/workflow-jobs/${jobId}`;
}
