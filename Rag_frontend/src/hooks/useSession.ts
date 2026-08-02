import { useCallback, useEffect, useState } from "react";
import { endSession, endSessionBeacon, initSession } from "../api/session";

const STORAGE_KEY = "rag_session_id";

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const existing = sessionStorage.getItem(STORAGE_KEY);
      if (existing) {
        if (!cancelled) {
          setSessionId(existing);
          setReady(true);
        }
        return;
      }
      try {
        const id = await initSession();
        sessionStorage.setItem(STORAGE_KEY, id);
        if (!cancelled) {
          setSessionId(id);
          setReady(true);
        }
      } catch (e) {
        console.error("failed to init session", e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    const handler = () => endSessionBeacon(sessionId);
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [sessionId]);

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

  return { sessionId, ready, newChat };
}
