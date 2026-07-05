export interface FounderRecord {
  id: string;
  organisation_id: string;
  company_id: string;
  created_by: string;
  name: string;
  title?: string | null;
  linkedin_url?: string | null;
  bio?: string | null;
}
