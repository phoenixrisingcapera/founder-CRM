import { ApiClient } from './client';

export interface DiligenceQuestionRecord {
  id: string;
  deal_id: string;
  question: string;
  category: string;
  status?: string;
  source?: string;
}

export interface DiligenceGenerationResponse {
  ai_run_id: string;
  deal_id: string;
  questions: DiligenceQuestionRecord[];
}

export function listDiligenceQuestions(
  client = new ApiClient(),
  dealId?: string,
): Promise<DiligenceQuestionRecord[]> {
  const query = dealId ? `?deal_id=${encodeURIComponent(dealId)}` : '';
  return client.get<DiligenceQuestionRecord[]>(`/diligence${query}`);
}

export function createDiligenceQuestion(
  payload: {
    deal_id: string;
    question: string;
    category: string;
    status?: string;
    source?: string;
  },
  client = new ApiClient(),
): Promise<DiligenceQuestionRecord> {
  return client.post<DiligenceQuestionRecord>('/diligence', payload);
}

export function generateDiligenceQuestions(
  dealId: string,
  client = new ApiClient(),
): Promise<DiligenceGenerationResponse> {
  return client.post<DiligenceGenerationResponse>(`/diligence/generate/${dealId}`, {});
}
