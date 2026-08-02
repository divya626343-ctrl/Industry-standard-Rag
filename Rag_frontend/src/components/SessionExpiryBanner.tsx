import { AlertDot } from "./icons/icons";

interface Props {
  remainingMs: number;
  isWarning: boolean;
}

function formatMinSec(ms: number): string {
  const totalSec = Math.max(0, Math.floor(ms / 1000));
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, "0")}`;
}

export function SessionExpiryBanner({ remainingMs, isWarning }: Props) {
  if (!isWarning) return null;

  return (
    <div className="expiry-banner">
      <AlertDot size={8} style={{ marginRight: 8 }} />
      <span>
        Your session ends in {formatMinSec(remainingMs)} due to inactivity — send a message to stay active.
      </span>
    </div>
  );
}
