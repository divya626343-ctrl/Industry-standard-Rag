import { useCallback, useEffect, useState } from "react";
import { getSessionStatus } from "../api/session";
import { ApiError } from "../api/client";

const POLL_INTERVAL_MS = 30 * 1000;
const WARNING_THRESHOLD_S = 4 * 60; // "ticker shows ~4 min before it could die", per your spec

export function useSessionExpiry(sessionId: string | null, onExpired: () => void) {
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);

  const poll = useCallback(async () => {
    if (!sessionId) return;
    try {
      const status = await getSessionStatus(sessionId);
      setRemainingSeconds(status.ttl_seconds);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        onExpired();
      } else {
        console.error("session status poll failed", e);
      }
    }
  }, [sessionId, onExpired]);

  useEffect(() => {
    if (!sessionId) return;
    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [sessionId, poll]);

  return {
    remainingSeconds,
    isWarning: remainingSeconds !== null && remainingSeconds <= WARNING_THRESHOLD_S,
    // Call after any confirmed activity (query sent, upload started) to reflect
    // the backend's own heartbeat-on-query refresh immediately, rather than
    // waiting up to 30s for the next scheduled poll to catch up.
    refreshNow: poll,
  };
}
