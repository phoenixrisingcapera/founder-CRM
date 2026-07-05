export interface SessionRecord {
  id: string;
  organisation_id: string;
  project_id?: string | null;
  created_by: string;
  title: string;
  session_type: string;
  status: string;
  agenda?: string | null;
  starts_at?: string | null;
}
