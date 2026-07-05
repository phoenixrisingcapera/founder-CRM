export interface AiCapabilityRecord {
  id: string;
  title: string;
  description: string;
  category: 'intro_discovery' | 'scoring' | 'memo' | 'followup' | 'conversation' | 'research';
  draft_only: boolean;
  status: 'ready' | 'coming_soon';
}
