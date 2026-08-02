import { API_BASE, ApiError } from "./client";

// FLAG: no DELETE route was present in documents.py or ingestion.py, the only
// two backend route files shared so far. This calls a guessed REST-ish shape
// (`DELETE /documents/{doc_id}?session_id=...`) that purges the doc's vectors
// from Qdrant, per what you described. CONFIRM the real route + method before
// relying on this — update this one function once you have it, nothing else
// in the app needs to change.
export async function deleteDocument(docId: string, sessionId: string): Promise<void> {
  const params = new URLSearchParams({ session_id: sessionId });
  const res = await fetch(`${API_BASE}/documents/${docId}?${params.toString()}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new ApiError(`delete failed (${res.status})`, res.status);
  }
}
