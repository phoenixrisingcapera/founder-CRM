export interface CompanyRecord {
  id: string;
  project_id?: string | null;
  name: string;
  website?: string;
  sector?: string;
  stage?: string;
  geography?: string;
  summary?: string | null;
}
