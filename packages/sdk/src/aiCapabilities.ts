import type { AiCapabilityRecord } from '../../types/src/ai';

const capabilitySeed: AiCapabilityRecord[] = [
  {
    id: 'ai_capability_find_warm_intros',
    title: 'Find Warm Intros',
    description: 'Rank likely intro paths using CRM relationships and deterministic scoring.',
    category: 'intro_discovery',
    draft_only: true,
    status: 'ready',
  },
  {
    id: 'ai_capability_score_contacts',
    title: 'Score Contact Fit',
    description: 'Explain why a contact matches the current founder or VC goal.',
    category: 'scoring',
    draft_only: true,
    status: 'ready',
  },
  {
    id: 'ai_capability_build_memo',
    title: 'Build Investment Memo',
    description: 'Draft a first-pass memo from notes, sources, and diligence.',
    category: 'memo',
    draft_only: true,
    status: 'ready',
  },
];

export async function listAiCapabilities(): Promise<AiCapabilityRecord[]> {
  return capabilitySeed;
}
