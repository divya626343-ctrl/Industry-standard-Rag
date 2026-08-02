import { API_BASE, request } from "./client";

export async function initSession(): Promise<string> {
  const data = await request<{ session_id: string }>("/session/init", { method: "POST" });
  return data.session_id;
}

// Fire-and-forget on tab close — sendBeacon can't read a response, and that's fine.
export function endSessionBeacon(sessionId: string): void {
  navigator.sendBeacon(`${API_BASE}/session/${sessionId}/end`);
}

// Explicit "New chat" action — uses fetch (not sendBeacon) since we want to know it completed.
export async function endSession(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/session/${sessionId}/end`, { method: "POST" });
}
