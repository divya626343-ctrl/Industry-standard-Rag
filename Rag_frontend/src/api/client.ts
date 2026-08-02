// Runtime-injected (Docker) takes priority over build-time (local `npm run dev`).
declare global {
  interface Window {
    __ENV__?: { VITE_API_URL?: string };
  }
}

export const API_BASE =
  window.__ENV__?.VITE_API_URL ||
  (import.meta.env.VITE_API_URL as string | undefined) ||
  "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  body?: unknown;
  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      // no JSON body, fine
    }
    throw new ApiError(`Request to ${path} failed (${res.status})`, res.status, body);
  }
  // some routes (e.g. /session/end) may return no content
  const text = await res.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}
