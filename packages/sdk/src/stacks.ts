import { ApiClient } from './client';
import type { StackRecord } from '../../types/src/stack';

export function listStacks(client = new ApiClient()): Promise<StackRecord[]> {
  return client.get<StackRecord[]>('/stacks');
}
