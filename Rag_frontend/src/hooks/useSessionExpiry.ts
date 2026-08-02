import { useCallback, useEffect, useRef, useState } from "react";

const SESSION_TTL_MS = 30 * 60 * 1000; // matches the documented 30-min inactivity sweep
const WARNING_THRESHOLD_MS = 4 * 60 * 1000; // "ticker shows ~4 min before it could die"

// FLAG: no GET /session/{id}/status (or similar TTL-check) endpoint has been
// confirmed in any backend file shared so far. The original context doc says
// the backend refreshes the session automatically whenever a query is
// processed -- so this hook tracks expiry client-side and resets on any
// confirmed action (send query / start upload) rather than polling a route
// that may not exist. If a real status endpoint shows up, swap the interval
// below for a poll against it -- everything downstream (the banner) stays the same.
export function useSessionExpiry(sessionId: string | null) {
  const deadlineRef = useRef(Date.now() + SESSION_TTL_MS);
  const [remainingMs, setRemainingMs] = useState(SESSION_TTL_MS);

  const resetTimer = useCallback(() => {
    deadlineRef.current = Date.now() + SESSION_TTL_MS;
    setRemainingMs(SESSION_TTL_MS);
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    resetTimer();
    const interval = setInterval(() => {
      setRemainingMs(Math.max(0, deadlineRef.current - Date.now()));
    }, 1000);
    return () => clearInterval(interval);
  }, [sessionId, resetTimer]);

  return {
    remainingMs,
    isWarning: remainingMs <= WARNING_THRESHOLD_MS,
    expired: remainingMs <= 0,
    resetTimer,
  };
}
