"use client";

import { useEffect, useRef, useState } from "react";

function formatRemaining(totalSeconds: number) {
  const seconds = Math.max(0, Math.ceil(totalSeconds));
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
  return `${minutes}m ${secs}s`;
}

export function ProgramCountdown({ seconds, onExpire, className = "", syncElapsedSeconds }: { seconds: number; onExpire?: () => void; className?: string; syncElapsedSeconds?: number }) {
  const [remaining, setRemaining] = useState(Math.max(0, seconds - (syncElapsedSeconds ?? 0)));
  const onExpireRef = useRef(onExpire);
  const syncExpiredForRef = useRef<number | null>(null);

  useEffect(() => { onExpireRef.current = onExpire; }, [onExpire]);

  useEffect(() => {
    // When the parent program shell supplies elapsedSeconds, this component
    // becomes a pure view of the shared shell clock. This prevents the
    // horizontal journey, locked-day page, and other countdowns from each
    // starting their own timers from slightly different fetch timestamps.
    if (syncElapsedSeconds !== undefined) {
      const next = Math.max(0, seconds - syncElapsedSeconds);
      setRemaining(next);

      if (next > 0) {
        syncExpiredForRef.current = null;
        return;
      }

      if (syncExpiredForRef.current === seconds) return;
      syncExpiredForRef.current = seconds;
      const expireTimer = window.setTimeout(() => onExpireRef.current?.(), 250);
      return () => window.clearTimeout(expireTimer);
    }

    syncExpiredForRef.current = null;
    const durationMs = Math.max(0, seconds) * 1000;
    const expiresAt = Date.now() + durationMs;
    let fired = false;
    let expireTimer: number | undefined;

    const fireExpired = () => {
      if (fired) return;
      fired = true;
      setRemaining(0);
      // Give the backend clock a tiny margin so a request at the exact boundary
      // cannot come back LOCKED because of sub-second clock skew.
      expireTimer = window.setTimeout(() => onExpireRef.current?.(), 250);
    };

    const tick = () => {
      const millisecondsLeft = expiresAt - Date.now();
      if (millisecondsLeft <= 0) {
        fireExpired();
        return;
      }
      setRemaining(Math.ceil(millisecondsLeft / 1000));
    };

    tick();
    const interval = window.setInterval(tick, 250);
    return () => {
      window.clearInterval(interval);
      if (expireTimer !== undefined) window.clearTimeout(expireTimer);
    };
  }, [seconds, syncElapsedSeconds]);

  const displayRemaining = syncElapsedSeconds !== undefined
    ? Math.max(0, seconds - syncElapsedSeconds)
    : remaining;

  return <span className={className} role="timer" aria-label={`Waktu hingga panduan berikutnya: ${formatRemaining(displayRemaining)}`} aria-live="polite">{formatRemaining(displayRemaining)}</span>;
}
