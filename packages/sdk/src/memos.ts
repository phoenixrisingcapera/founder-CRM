import { ApiClient } from './client';
import type { MemoRecord } from '../../types/src/memo';

export function listMemos(client = new ApiClient()): Promise<MemoRecord[]> {
  return client.get<MemoRecord[]>('/memos');
}

export function getMemo(memoId: string, client = new ApiClient()): Promise<MemoRecord> {
  return client.get<MemoRecord>(`/memos/${memoId}`);
}

export function createMemo(
  payload: {
    deal_id: string;
    title: string;
    summary?: string;
    content?: string;
    status?: string;
    source?: string;
  },
  client = new ApiClient(),
): Promise<MemoRecord> {
  return client.post<MemoRecord>('/memos', payload);
}

export function generateMemo(dealId: string, client = new ApiClient()): Promise<{ ai_run_id: string; memo: MemoRecord }> {
  return client.post<{ ai_run_id: string; memo: MemoRecord }>(`/memos/generate/${dealId}`, {});
}
