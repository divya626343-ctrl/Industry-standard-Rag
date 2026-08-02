import type { ChunkingStrategy } from "../types";
import { CloseIcon } from "./icons/icons";

const STRATEGIES: { value: ChunkingStrategy; label: string }[] = [
  { value: "recursive_token", label: "Recursive token" },
  { value: "semantic", label: "Semantics" },
  { value: "fixed", label: "Fixed" },
];

interface Props {
  sessionId: string;
  onChoose: (s: ChunkingStrategy) => void;
  onDismiss: () => void;
}

export function StrategyPopover({ sessionId, onChoose, onDismiss }: Props) {
  return (
    <div className="popover-overlay" onClick={onDismiss}>
      <div className="popover-card" onClick={(e) => e.stopPropagation()}>
        <button className="popover-close" onClick={onDismiss} aria-label="Dismiss">
          <CloseIcon />
        </button>

        <div className="popover-header">
          <span className="popover-title">Session initiated</span>
          <span className="popover-session-id">{sessionId}</span>
        </div>

        <p className="popover-body">
          Before moving forward, please select your preferred chunking strategy. If you skip this,
          a default strategy will be used automatically.
        </p>

        <div className="popover-strategies">
          {STRATEGIES.map((s) => (
            <button key={s.value} className="popover-strategy-btn" onClick={() => onChoose(s.value)}>
              {s.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
