import { ApiClient } from './client';
import type { ProjectRecord } from '../../types/src/project';

export function listProjects(client = new ApiClient()): Promise<ProjectRecord[]> {
  return client.get<ProjectRecord[]>('/projects');
}

export function getProject(projectId: string, client = new ApiClient()): Promise<ProjectRecord> {
  return client.get<ProjectRecord>(`/projects/${projectId}`);
}

export function createProject(
  payload: { name: string; description?: string; status?: string },
  client = new ApiClient(),
): Promise<ProjectRecord> {
  return client.post<ProjectRecord>('/projects', payload);
}
