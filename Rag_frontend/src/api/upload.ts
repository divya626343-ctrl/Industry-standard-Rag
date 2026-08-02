import { API_BASE, ApiError, request } from "./client";
import type { UploadQueuedResponse, TaskStatusResponse } from "../types";

export async function uploadDocument(
  file: File,
  sessionId: string,
  chosenStrategy?: string | null,
  org?: string | null,
): Promise<UploadQueuedResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("session_id", sessionId);
  if (chosenStrategy) form.append("chosen_strategy", chosenStrategy);
  if (org) form.append("org", org);

  const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) {
    let body: unknown;
    try { body = await res.json(); } catch { /* no body */ }
    throw new ApiError(`upload failed (${res.status})`, res.status, body);
  }
  return res.json();
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  return request<TaskStatusResponse>(`/task-status/${taskId}`);
}
