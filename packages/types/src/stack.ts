export interface StackRecord {
  id: string;
  organisation_id: string;
  project_id?: string | null;
  created_by: string;
  name: string;
  focus_area?: string | null;
  status: string;
  tool_count: number;
  notes?: string | null;
}
