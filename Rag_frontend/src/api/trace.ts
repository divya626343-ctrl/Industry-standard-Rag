import { request } from "./client";
import type { TraceStep } from "../types";

export async function getLatestTrace(sessionId: string): Promise<{ session_id: string; trace: TraceStep[] }> {
  return request(`/trace/${sessionId}/latest`);
}
