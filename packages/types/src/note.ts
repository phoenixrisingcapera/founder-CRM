export interface NoteRecord {
  id: string;
  title: string;
  body: string;
  entity_type?: string | null;
  entity_id?: string | null;
  status: string;
}
