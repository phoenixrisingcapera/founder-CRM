import type { Cookies } from '@sveltejs/kit';
import type { DesignBatchDetail, DesignBatchPreview } from '@deck-aistack-codes/shared';
import { deckProductApiPath } from '$lib/contracts';
import { requireBackendAuthHeaders } from '$server/backendAuth';
import { requireBackendUrl } from '$server/backendApi';

function requireCookies(cookies: Cookies | undefined): Cookies {
  if (!cookies) {
    throw new Error('Authenticated backend access requires request cookies.');
  }
  return cookies;
}

function normalizeBatchPreview(payload: Record<string, unknown>): DesignBatchPreview {
  return {
    id: String(payload.id ?? ''),
    deckId: String(payload.deckId ?? ''),
    batchNumber: Number(payload.batchNumber ?? 0),
    batchName: payload.batchName ? String(payload.batchName) : null,
    scopeType: String(payload.scopeType ?? 'selected_slides') as DesignBatchPreview['scopeType'],
    selectedSlideCount: Number(payload.selectedSlideCount ?? 0),
    status: String(payload.status ?? 'completed') as DesignBatchPreview['status'],
    createdAt: String(payload.createdAt ?? new Date().toISOString())
  };
}

function normalizeBatchDetail(payload: Record<string, unknown>): DesignBatchDetail {
  return {
    ...normalizeBatchPreview(payload),
    prompt: String(payload.prompt ?? ''),
    audienceLabel: payload.audienceLabel ? String(payload.audienceLabel) : null,
    selectedSlideIds: ((payload.selectedSlideIds ?? []) as unknown[]).map((item) => String(item)),
    candidateSlides: ((payload.candidateSlides ?? []) as Record<string, unknown>[]).map((candidate) => ({
      id: String(candidate.id ?? ''),
      batchId: String(candidate.batchId ?? ''),
      sourceSlideId: candidate.sourceSlideId ? String(candidate.sourceSlideId) : null,
      slideIndex: Number(candidate.slideIndex ?? 0),
      title: String(candidate.title ?? 'Untitled slide'),
      headline: String(candidate.headline ?? ''),
      summary: String(candidate.summary ?? ''),
      status: String(candidate.status ?? 'reviewable') as DesignBatchDetail['candidateSlides'][number]['status']
    }))
  };
}

export async function listLatestDesignBatches(deckId: string, limit = 3, cookies?: Cookies): Promise<DesignBatchPreview[]> {
  const backendUrl = requireBackendUrl();
  const response = await fetch(`${backendUrl}${deckProductApiPath(`/decks/${deckId}/versions?limit=${limit}`)}`, {
    headers: requireBackendAuthHeaders(requireCookies(cookies))
  });
  if (!response.ok) {
    throw new Error('Could not load persisted design versions from the backend.');
  }

  const payload = (await response.json()) as { batches?: Record<string, unknown>[] };
  return (payload.batches ?? []).map(normalizeBatchPreview);
}

export async function getDesignBatchById(deckId: string, batchId: string, cookies?: Cookies): Promise<DesignBatchDetail | undefined> {
  const backendUrl = requireBackendUrl();
  const response = await fetch(`${backendUrl}${deckProductApiPath(`/decks/${deckId}/versions/${batchId}`)}`, {
    headers: requireBackendAuthHeaders(requireCookies(cookies))
  });
  if (!response.ok) {
    if (response.status === 404) {
      return undefined;
    }

    throw new Error('Could not load the requested design version.');
  }

  const payload = (await response.json()) as { batch?: Record<string, unknown> };
  return payload.batch ? normalizeBatchDetail(payload.batch) : undefined;
}
