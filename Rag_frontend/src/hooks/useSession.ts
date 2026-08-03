import { useCallback, useEffect, useRef, useState } from "react";
import { endSession, endSessionBeacon, initSession } from "../api/session";
import { API_BASE } from "../api/client";

const STORAGE_KEY = "rag_session_id";

export function clearStoredSessionId() {
  sessionStorage.removeItem(STORAGE_KEY);
}

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // React 18 StrictMode intentionally double-fires effects in dev (mount -> cleanup
  // -> mount again) to surface bugs. Without this guard that meant two concurrent
  // POST /session/init calls on every load -- wasteful, and a source of confusing
  // "which session is real" bugs. This ensures boot only actually runs once.
  const bootedRef = useRef(false);

  const boot = useCallback(async () => {
    setError(null);
    const existing = sessionStorage.getItem(STORAGE_KEY);
    if (existing) {
      setSessionId(existing);
      setReady(true);
      return;
    }
    try {
      const id = await initSession();
      sessionStorage.setItem(STORAGE_KEY, id);
      setSessionId(id);
      setReady(true);
    } catch (e) {
      // This is the failure that used to hang silently at "Starting session..."
      // with nothing but a console.error -- now it actually surfaces to the UI.
      console.error("failed to init session", e);
      setError(
        `Couldn't reach the backend at ${API_BASE}. Check that it's running and that ` +
          `this origin is in CORS_ALLOWED_ORIGINS.`,
      );
      setReady(true); // stop showing the loading state — show the error instead
    }
  }, []);

  useEffect(() => {
    if (bootedRef.current) return;
    bootedRef.current = true;
    boot();
  }, [boot]);

  useEffect(() => {
    if (!sessionId) return;
    const handler = () => endSessionBeacon(sessionId);
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [sessionId]);

  const retryInit = useCallback(() => {
    bootedRef.current = false;
    setReady(false);
    boot();
  }, [boot]);

  const newChat = useCallback(async () => {
    if (sessionId) {
      try {
        await endSession(sessionId);
      } catch (e) {
        console.error("failed to end session cleanly, continuing anyway", e);
      }
    }
    sessionStorage.removeItem(STORAGE_KEY);
    const id = await initSession();
    sessionStorage.setItem(STORAGE_KEY, id);
    setSessionId(id);
    return id;
  }, [sessionId]);

  return { sessionId, ready, error, retryInit, newChat };
}
