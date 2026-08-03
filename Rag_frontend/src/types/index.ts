// Strategy names per your Desktop mockup screenshots (Recursive token / Semantics / Fixed).
export type ChunkingStrategy = "fixed" | "recursive_token" | "semantic";

export interface UploadQueuedResponse {
  status: "queued" | "duplicate";
  task_id: string | null;
}

export interface TaskStatusResult {
  doc_id: string;
  chunks_indexed: number;
  strategy: string;
  status: string;
}

export interface TaskStatusResponse {
  task_id: string;
  state: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE";
  result?: TaskStatusResult;
  error?: string;
}

export type DocStatus = "queued" | "processing" | "indexed" | "failed";

export interface DocumentItem {
  id: string;       // task_id once known, temp id before that
  taskId: string;
  docId?: string;
  filename: string;
  status: DocStatus;
  error?: string;
}

export interface Citation {
  chunk_id: string;
  doc_id?: string;
  page_number?: number;
  source_collection: "shared" | "session";
}

export type CitationsMap = Record<string, Citation>;

export type MessageStatus = "streaming" | "done" | "error" | "guardrail";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: MessageStatus;
  citations?: CitationsMap;
  statusText?: string;
  isLatest?: boolean;
}

export interface TraceStep {
  node: string;
  event?: string;
  started_at?: number;
  completed_at?: number;
  elapsed_ms?: number;
  detail?: Record<string, unknown>;
}

export interface CitationLocation {
  doc_id: string;
  source_file_uri: string;
  page_number: number;
  bbox: [number, number, number, number];
}
