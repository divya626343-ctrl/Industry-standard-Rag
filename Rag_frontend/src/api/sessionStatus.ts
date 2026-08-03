import { request } from "./client";

export interface SessionStatus {
  session_id: string;
  ttl_seconds: number;
}

// Returns null on 404 (expired or not found) rather than throwing, since
// that's an expected, meaningful state for the polling hook to react to.
export async function getSessionStatus(sessionId: string): Promise<SessionStatus | null> {
  try {
    return await request<SessionStatus>(`/session/${sessionId}/status`);
  } catch (e) {
    if (e && typeof e === "object" && "status" in e && (e as { status: number }).status === 404) {
      return null;
    }
    throw e;
  }
}
