import { error, type Cookies } from '@sveltejs/kit';
import { createHash } from 'node:crypto';
import { requireBackendAuthHeaders } from '$server/backendAuth';
import { extractErrorMessage, requireBackendUrl } from '$server/backendApi';

export type SmartDeckGenerationSubmission = {
  deckId: string;
  scope?: 'selected_slides' | 'current_slide' | 'selected_element';
  selectedSourceSlideIds: string[];
  instruction: string;
  deckType: string;
  audience: string | null;
  preferredModel: string | null;
  selectedElementId: string | null;
  selectedSubject: string | null;
  detectedSubjects: Array<Record<string, unknown>>;
  actionId: string | null;
  actionPrompt: string | null;
  userPrompt: string;
  latestBatchId: string | null;
  idempotencyKey: string;
};

export type ApplyDesignVersionSubmission = {
  designVersionId: string;
  idempotencyKey: string;
};

export type LlmParallelizationSubmission = {
  deckId: string;
  prompt: string;
  selectedSourceSlideIds: string[];
  partitionCount: number;
  batchSize: number;
  preferredModel: string | null;
  idempotencyKey: string;
};

function selectedIdsForScope(payload: {
  scope?: 'selected_slides' | 'current_slide' | 'selected_element';
  selectedSlideIds?: string[];
  currentSlideId?: string | null;
}) {
  if (payload.scope === 'current_slide') return payload.currentSlideId ? [payload.currentSlideId] : [];
  return payload.selectedSlideIds ?? [];
}

export async function readSmartDeckGenerationSubmission(request: Request): Promise<SmartDeckGenerationSubmission> {
  const payload = (await request.json().catch(() => null)) as {
    deckId?: string;
    scope?: 'selected_slides' | 'current_slide' | 'selected_element';
    selectedSlideIds?: string[];
    currentSlideId?: string | null;
    selectedElementId?: string | null;
    instruction?: string;
    intentType?: 'redesign_slides';
    outputMode?: 'editable_slide_versions';
    deckType?: string;
    audience?: string | null;
    preferredModel?: string | null;
    selectedSubject?: string | null;
    detectedSubjects?: Array<Record<string, unknown>>;
    actionId?: string | null;
    actionPrompt?: string | null;
    userPrompt?: string | null;
    latestBatchId?: string | null;
  } | null;

  if (!payload?.deckId) {
    throw error(400, 'deckId is required.');
  }
  if (!payload.instruction?.trim()) {
    throw error(400, 'instruction is required.');
  }
  if (payload.intentType && payload.intentType !== 'redesign_slides') {
    throw error(400, 'intentType must be redesign_slides.');
  }
  if (payload.outputMode && payload.outputMode !== 'editable_slide_versions') {
    throw error(400, 'outputMode must be editable_slide_versions.');
  }

  const selectedSourceSlideIds = selectedIdsForScope(payload);
  if (selectedSourceSlideIds.length === 0) {
    throw error(400, 'Select one or more slides to redesign.');
  }

  const idempotencySeed = JSON.stringify({
    deckId: payload.deckId,
    selectedSourceSlideIds,
    instruction: payload.instruction.trim(),
    deckType: payload.deckType ?? 'unknown',
    audience: payload.audience ?? null,
    preferredModel: payload.preferredModel ?? null,
    selectedSubject: payload.selectedSubject ?? null,
    actionId: payload.actionId ?? null,
    actionPrompt: payload.actionPrompt ?? null,
    userPrompt: payload.userPrompt ?? payload.instruction.trim(),
    latestBatchId: payload.latestBatchId ?? null
  });

  return {
    deckId: payload.deckId,
    scope: payload.scope ?? 'selected_slides',
    selectedSourceSlideIds,
    instruction: payload.instruction.trim(),
    deckType: payload.deckType ?? 'unknown',
    audience: payload.audience ?? null,
    preferredModel: payload.preferredModel ?? null,
    selectedElementId: payload.selectedElementId ?? null,
    selectedSubject: payload.selectedSubject ?? null,
    detectedSubjects: payload.detectedSubjects ?? [],
    actionId: payload.actionId ?? null,
    actionPrompt: payload.actionPrompt ?? null,
    userPrompt: payload.userPrompt ?? payload.instruction.trim(),
    latestBatchId: payload.latestBatchId ?? null,
    idempotencyKey: `workflow:${payload.deckId}:${createHash('sha256').update(idempotencySeed).digest('hex')}`
  };
}

export async function readApplyDesignVersionSubmission(request: Request): Promise<ApplyDesignVersionSubmission> {
  const payload = (await request.json().catch(() => null)) as { designVersionId?: string; versionId?: string } | null;
  const designVersionId = payload?.designVersionId ?? payload?.versionId;

  if (!designVersionId) {
    throw error(400, 'designVersionId is required.');
  }

  return {
    designVersionId,
    idempotencyKey: `apply:${designVersionId}`
  };
}

export async function readLlmParallelizationSubmission(request: Request): Promise<LlmParallelizationSubmission> {
  const payload = (await request.json().catch(() => null)) as {
    deckId?: string;
    prompt?: string;
    selectedSourceSlideIds?: string[];
    partitionCount?: number;
    batchSize?: number;
    preferredModel?: string | null;
  } | null;

  if (!payload?.deckId) {
    throw error(400, 'deckId is required.');
  }
  if (!payload.prompt?.trim()) {
    throw error(400, 'prompt is required.');
  }
  if (!Array.isArray(payload.selectedSourceSlideIds) || payload.selectedSourceSlideIds.length === 0) {
    throw error(400, 'selectedSourceSlideIds is required.');
  }

  const partitionCount = Number.isFinite(payload.partitionCount) ? Math.max(1, Math.min(32, Math.trunc(payload.partitionCount ?? 4))) : 4;
  const batchSize = Number.isFinite(payload.batchSize) ? Math.max(1, Math.min(64, Math.trunc(payload.batchSize ?? 8))) : 8;
  const normalizedSlideIds = Array.from(new Set(payload.selectedSourceSlideIds.map((slideId) => String(slideId).trim()).filter(Boolean)));

  if (normalizedSlideIds.length === 0) {
    throw error(400, 'selectedSourceSlideIds is required.');
  }

  const idempotencySeed = JSON.stringify({
    deckId: payload.deckId,
    prompt: payload.prompt.trim(),
    selectedSourceSlideIds: normalizedSlideIds,
    partitionCount,
    batchSize,
    preferredModel: payload.preferredModel ?? null
  });

  return {
    deckId: payload.deckId,
    prompt: payload.prompt.trim(),
    selectedSourceSlideIds: normalizedSlideIds,
    partitionCount,
    batchSize,
    preferredModel: payload.preferredModel ?? null,
    idempotencyKey: `spark:${payload.deckId}:${createHash('sha256').update(idempotencySeed).digest('hex')}`
  };
}

export async function submitWorkflowCommand<TResponse>(
  fetcher: typeof fetch,
  cookies: Cookies,
  path: string,
  fallbackMessage: string,
  init: RequestInit = {}
): Promise<TResponse> {
  const backendUrl = requireBackendUrl();
  const headers = new Headers(init.headers);
  for (const [key, value] of Object.entries(requireBackendAuthHeaders(cookies))) {
    headers.set(key, String(value));
  }

  const response = await fetcher(`${backendUrl}${path}`, {
    ...init,
    headers
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw error(response.status, extractErrorMessage(payload, fallbackMessage));
  }
  return payload as TResponse;
}
