import { ApiClient } from './client';
import type { LinkedInIntroPathRecord, LinkedInIntroPathSearchPayload } from '../../types/src/linkedin';

export function searchCrmIntroPaths(
  payload: LinkedInIntroPathSearchPayload,
  client = new ApiClient(),
): Promise<LinkedInIntroPathRecord[]> {
  return client.post<LinkedInIntroPathRecord[]>('/crm/intro-paths/search', payload);
}
