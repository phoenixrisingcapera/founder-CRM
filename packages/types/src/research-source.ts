export interface ResearchSourceRecord {
  id: string;
  organisation_id: string;
  project_id?: string | null;
  created_by: string;
  title: string;
  source_type: string;
  url?: string | null;
  status: string;
  notes?: string | null;
}

export interface SourceChunkRecord {
  id: string;
  organisation_id: string;
  snapshot_id: string;
  chunk_index: number;
  heading?: string | null;
  body_markdown: string;
  character_count: number;
}

export interface CitationRecord {
  id: string;
  organisation_id: string;
  snapshot_id: string;
  chunk_id?: string | null;
  label: string;
  quote_text: string;
  locator?: string | null;
}

export interface SourceSnapshotRecord {
  id: string;
  organisation_id: string;
  source_id: string;
  created_by: string;
  title?: string | null;
  content_hash: string;
  body_markdown: string;
  visibility: string;
  captured_at: string;
  chunks: SourceChunkRecord[];
  citations: CitationRecord[];
}
