export interface InvestorRecord {
  id: string;
  name: string;
  firm_name?: string | null;
  investor_type?: string | null;
  stage_focus?: string | null;
  geography?: string | null;
  thesis?: string | null;
  status: string;
}
