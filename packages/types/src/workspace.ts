export interface WorkspaceRecord {
  id: string;
  name: string;
  slug: string;
}

export interface WorkspaceCounts {
  projects: number;
  companies: number;
  founders: number;
  deals: number;
  memos: number;
  active_deals: number;
  draft_memos: number;
}

export interface WorkspaceSummaryItem {
  id: string;
  title: string;
  subtitle?: string | null;
  status?: string | null;
}

export interface WorkspaceSummaryRecord {
  workspace: WorkspaceRecord;
  counts: WorkspaceCounts;
  recent_projects: WorkspaceSummaryItem[];
  recent_companies: WorkspaceSummaryItem[];
  recent_deals: WorkspaceSummaryItem[];
  recent_memos: WorkspaceSummaryItem[];
}
