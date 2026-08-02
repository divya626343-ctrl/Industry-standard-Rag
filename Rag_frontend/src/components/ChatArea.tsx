import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";
import { QueryInput } from "./QueryInput";

interface Props {
  messages: ChatMessage[];
  sessionId: string;
  queryDisabled: boolean;
  queryDisabledReason?: string;
  onSend: (q: string) => void;
  onRetry: () => void;
  onCitationClick: (citationKey: string) => void;
  onBackgroundClick: () => void;
}

export function ChatArea({
  messages,
  sessionId,
  queryDisabled,
  queryDisabledReason,
  onSend,
  onRetry,
  onCitationClick,
  onBackgroundClick,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const isEmpty = messages.length === 0;

  return (
    <main className="chat-area" onClick={onBackgroundClick}>
      <div className={`chat-scroll${isEmpty ? " chat-scroll-empty" : ""}`} ref={scrollRef}>
        {messages.map((m) => (
          <div key={m.id} onClick={(e) => e.stopPropagation()}>
            <MessageBubble message={m} sessionId={sessionId} onCitationClick={onCitationClick} onRetry={onRetry} />
          </div>
        ))}
      </div>

      <div onClick={(e) => e.stopPropagation()}>
        <QueryInput disabled={queryDisabled} disabledReason={queryDisabledReason} onSend={onSend} />
      </div>
    </main>
  );
}
