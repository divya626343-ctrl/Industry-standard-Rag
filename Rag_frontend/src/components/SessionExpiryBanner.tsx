import { AlertDot } from "./icons/icons";

interface Props {
  remainingSeconds: number | null;
  isWarning: boolean;
}

function formatMinSec(totalSec: number): string {
  const s = Math.max(0, Math.floor(totalSec));
  const min = Math.floor(s / 60);
  const sec = s % 60;
  return `${min}:${sec.toString().padStart(2, "0")}`;
}

export function SessionExpiryBanner({ remainingSeconds, isWarning }: Props) {
  if (!isWarning || remainingSeconds === null) return null;

  return (
    <div className="expiry-banner">
      <AlertDot size={8} style={{ marginRight: 8 }} />
      <span>
        Your session ends in {formatMinSec(remainingSeconds)} due to inactivity — send a message to stay active.
      </span>
    </div>
  );
}
