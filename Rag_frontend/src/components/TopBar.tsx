import type { ChunkingStrategy } from "../types";
import { StrategyDropdown } from "./StrategyDropdown";
import { NewChatIcon } from "./icons/icons";

interface Props {
  strategy: ChunkingStrategy | null;
  strategyLocked: boolean;
  onStrategyChange: (s: ChunkingStrategy) => void;
  onNewChat: () => void;
}

export function TopBar({ strategy, strategyLocked, onStrategyChange, onNewChat }: Props) {
  return (
    <header className="top-bar">
      <span className="logo">ZX Bank</span>
      <div className="top-bar-actions">
        <StrategyDropdown value={strategy} locked={strategyLocked} onChange={onStrategyChange} />
        <button className="new-chat-btn" onClick={onNewChat}>
          <NewChatIcon size={15} style={{ marginRight: 6 }} />
          New chat
        </button>
      </div>
    </header>
  );
}
