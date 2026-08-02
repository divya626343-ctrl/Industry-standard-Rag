import { API_BASE } from "./client";
import type { CitationsMap } from "../types";

export type StreamEvent =
  | { type: "status"; node: string; message: string }
  | { type: "done"; exit_stage: string | null; message: string; citations: CitationsMap }
  | { type: "error"; message: string };

// query.py's route is `async def query(query: str, session_id: str)` with no
// Body()/Pydantic model -- FastAPI treats bare scalar args like this as query
// params by default, so this is POST /query?query=...&session_id=..., NOT a JSON body.
export async function streamQuery(
  query: string,
  sessionId: string,
  onEvent: (evt: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const params = new URLSearchParams({ query, session_id: sessionId });
  const res = await fetch(`${API_BASE}/query?${params.toString()}`, {
    method: "POST",
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`query stream failed to start (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? ""; // last (possibly incomplete) chunk stays buffered

    for (const raw of parts) {
      const line = raw.trim();
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (!payload || payload === "[DONE]") continue;
      try {
        onEvent(JSON.parse(payload) as StreamEvent);
      } catch (e) {
        console.error("failed to parse SSE event", payload, e);
      }
    }
  }
}
