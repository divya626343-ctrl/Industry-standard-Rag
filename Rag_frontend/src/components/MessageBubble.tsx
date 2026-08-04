import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { ChatMessage, TraceStep } from "../types";
import { getLatestTrace } from "../api/trace";
import { AlertTriangleIcon, AlertCircleIcon, DropdownChevronIcon } from "./icons/icons";

interface Props {
  message: ChatMessage;
  sessionId: string;
  onCitationClick: (citationKey: string) => void;
  onRetry: () => void;
}

function TraceSection({ sessionId }: { sessionId: string }) {
  const [open, setOpen] = useState(false);
  const [trace, setTrace] = useState<TraceStep[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!open || trace || loading) return;
    setLoading(true);
    getLatestTrace(sessionId)
      .then((res) => setTrace(res.trace))
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  }, [open, trace, loading, sessionId]);

  return (
    <div className="trace-section">
      <button className="trace-toggle" onClick={() => setOpen((o) => !o)}>
        <DropdownChevronIcon size={14} style={{ transform: open ? "rotate(180deg)" : "none" }} />
        <span>How this answer was generated</span>
      </button>
      {open && (
        <div className="trace-body">
          {loading && <p className="trace-loading">Loading trace...</p>}
          {failed && <p className="trace-loading">Trace unavailable.</p>}
          {trace &&
            trace.map((step, i) => (
              <div className="trace-row" key={i}>
                <span className="trace-node">{step.node}</span>
                {typeof step.elapsed_ms === "number" && <span className="trace-time">{step.elapsed_ms}ms</span>}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

export function MessageBubble({ message, sessionId, onCitationClick, onRetry }: Props) {
  if (message.role === "user") {
    return (
      <div className="msg-row msg-row-user">
        <div className="bubble bubble-user">{message.content}</div>
      </div>
    );
  }

  // guardrail exit — visually distinct from a real crash
  if (message.status === "guardrail") {
    return (
      <div className="msg-row msg-row-assistant">
        <div className="bubble bubble-guardrail">
          <div className="bubble-guardrail-row">
            <AlertTriangleIcon size={15} style={{ marginRight: 6, flexShrink: 0, color: "var(--error-text)" }} />
            <span>{message.content}</span>
          </div>
          {message.isLatest && <TraceSection sessionId={sessionId} />}
        </div>
      </div>
    );
  }

  if (message.status === "error") {
    return (
      <div className="msg-row msg-row-assistant">
        <div className="bubble bubble-error">
          <div className="bubble-error-row">
            <AlertCircleIcon size={15} style={{ marginRight: 6, flexShrink: 0, color: "var(--error-text)" }} />
            <span>{message.content || "Connection lost."}</span>
            <button className="retry-btn" onClick={onRetry}>
              Retry
            </button>
          </div>
          {/* Backend writes append_trace() on the crash path too (see runner_graph_streaming.py's
              except block) -- the trace up to the point of failure is genuinely useful here for
              figuring out which node broke, so it's worth surfacing even on a hard error. */}
          {message.isLatest && <TraceSection sessionId={sessionId} />}
        </div>
      </div>
    );
  }

  if (message.status === "streaming") {
    return (
      <div className="msg-row msg-row-assistant">
        <div className="bubble bubble-assistant bubble-loading">
          <span className="spinner" />
          <span>{message.statusText || "Thinking..."}</span>
        </div>
      </div>
    );
  }

  // done — render markdown + inline citation chips + trace (latest only)
  const citationEntries = message.citations ? Object.entries(message.citations) : [];

  return (
    <div className="msg-row msg-row-assistant">
      <div className="bubble bubble-assistant">
        <div className="answer-markdown">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {citationEntries.length > 0 && (
          <div className="citation-chips">
            {citationEntries.map(([key]) => (
              <button key={key} className="citation-chip" onClick={() => onCitationClick(key)}>
                [{key}]
              </button>
            ))}
          </div>
        )}

        {message.isLatest && <TraceSection sessionId={sessionId} />}
      </div>
    </div>
  );
}
