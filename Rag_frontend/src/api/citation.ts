import { API_BASE, ApiError, request } from "./client";
import type { CitationLocation } from "../types";

export async function getCitationLocation(
  chunkId: string,
  sourceCollection: string,
  sessionId: string,
): Promise<CitationLocation> {
  const params = new URLSearchParams({ source_collection: sourceCollection, session_id: sessionId });
  return request<CitationLocation>(`/citation/${chunkId}/location?${params.toString()}`);
}

// Only call this once the viewer is actually open — matches the fast-then-heavy
// two-call design confirmed in documents.py (location is cheap, file is not).
export async function getCitationFileBlob(
  chunkId: string,
  sourceCollection: string,
  sessionId: string,
): Promise<Blob> {
  const params = new URLSearchParams({ source_collection: sourceCollection, session_id: sessionId });
  const res = await fetch(`${API_BASE}/citation/${chunkId}/file?${params.toString()}`);
  if (!res.ok) {
    throw new ApiError(`citation file fetch failed (${res.status})`, res.status);
  }
  return res.blob();
}
