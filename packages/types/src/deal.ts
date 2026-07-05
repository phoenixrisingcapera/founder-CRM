export interface DealRecord {
  id: string;
  project_id?: string | null;
  company_id?: string;
  name: string;
  status?: string;
  stage?: string;
  thesis_fit?: string;
}
