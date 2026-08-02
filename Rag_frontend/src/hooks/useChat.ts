import { useCallback, useState } from "react";
import { streamQuery } from "../api/query";
import type { ChatMessage } from "../types";

let idCounter = 0;
const nextId = () => `m${++idCounter}-${Date.now()}`;

export function useChat(sessionId: string | null, onActivity?: () => void) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const send = useCallback(
    async (query: string) => {
      if (!sessionId || !query.trim() || isStreaming) return;
      onActivity?.();

      const userMsg: ChatMessage = { id: nextId(), role: "user", content: query };
      const assistantId = nextId();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        status: "streaming",
        statusText: "Thinking...",
        isLatest: true,
      };

      setMessages((prev) => [...prev.map((m) => ({ ...m, isLatest: false })), userMsg, assistantMsg]);
      setIsStreaming(true);

      try {
        await streamQuery(query, sessionId, (evt) => {
          if (evt.type === "status") {
            setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, statusText: evt.message } : m)));
          } else if (evt.type === "done") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      content: evt.message,
                      citations: evt.citations,
                      status: evt.exit_stage ? "guardrail" : "done",
                      statusText: undefined,
                    }
                  : m,
              ),
            );
          } else if (evt.type === "error") {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: evt.message, status: "error", statusText: undefined } : m)),
            );
          }
        });
      } catch (e) {
        console.error("stream failed", e);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: "Connection lost.", status: "error", statusText: undefined } : m,
          ),
        );
      } finally {
        setIsStreaming(false);
      }
    },
    [sessionId, isStreaming, onActivity],
  );

  const retryLast = useCallback(() => {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (lastUser) send(lastUser.content);
  }, [messages, send]);

  const reset = useCallback(() => setMessages([]), []);

  return { messages, send, retryLast, isStreaming, reset };
}
