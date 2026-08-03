import { API_BASE, ApiError } from "./client";

// Confirmed against documents_router in documents.py: DELETE /documents/{doc_id}?session_id=...
// -> {"status": "deleted", "doc_id": ...}, 404 if not found, 500 on backend delete failure.
export async function deleteDocument(docId: string, sessionId: string): Promise<void> {
  const params = new URLSearchParams({ session_id: sessionId });
  const res = await fetch(`${API_BASE}/documents/${docId}?${params.toString()}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new ApiError(`delete failed (${res.status})`, res.status);
  }
}
