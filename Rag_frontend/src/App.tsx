import { useCallback, useMemo, useState } from "react";
import { useSession, clearStoredSessionId } from "./hooks/useSession";
import { useSessionExpiry } from "./hooks/useSessionExpiry";
import { useDocuments } from "./hooks/useDocuments";
import { useChat } from "./hooks/useChat";
import { TopBar } from "./components/TopBar";
import { SessionExpiryBanner } from "./components/SessionExpiryBanner";
import { StrategyPopover } from "./components/StrategyPopover";
import { DocumentsPanel } from "./components/DocumentsPanel";
import { ChatArea } from "./components/ChatArea";
import { CitationViewer } from "./components/CitationViewer";
import { DocumentsPanelToggleIcon } from "./components/icons/icons";
import type { ChunkingStrategy, Citation } from "./types";

const DEFAULT_STRATEGY: ChunkingStrategy = "semantic";

export default function App() {
  const { sessionId, ready, error, retryInit, newChat } = useSession();

  const handleExpired = useCallback(() => {
    // Genuine 404 from /session/{id}/status -- the session is actually gone
    // server-side. Clear the stale id and reload; boot will init a fresh one.
    clearStoredSessionId();
    window.location.reload();
  }, []);

  const { remainingSeconds, isWarning, refreshNow } = useSessionExpiry(sessionId, handleExpired);

  const [strategy, setStrategy] = useState<ChunkingStrategy | null>(null);
  const [popoverDismissed, setPopoverDismissed] = useState(false);
  const [docsPanelOpen, setDocsPanelOpen] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  const { documents, upload, remove, hasPendingUpload } = useDocuments(sessionId, strategy, refreshNow);
  const { messages, send, retryLast, isStreaming } = useChat(sessionId, refreshNow);

  // Locks the instant either a first upload or first message has happened —
  // matches the confirmed non-blocking-popover, lock-on-first-action design.
  const strategyLocked = documents.length > 0 || messages.length > 0;

  const effectiveStrategy = strategy ?? DEFAULT_STRATEGY;

  const showPopover = ready && !!sessionId && !popoverDismissed && !strategyLocked;

  const latestAssistantCitations = useMemo(() => {
    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && m.citations);
    return lastAssistant?.citations ?? null;
  }, [messages]);

  const handleCitationClick = (key: string) => {
    const citation = latestAssistantCitations?.[key];
    if (citation) setActiveCitation(citation);
  };

  const handleNewChat = async () => {
    await newChat();
    setStrategy(null);
    setPopoverDismissed(false);
    setDocsPanelOpen(false);
    setActiveCitation(null);
    refreshNow();
    // messages/documents reset happens implicitly: both hooks are keyed off
    // sessionId internally via their API calls, but their local React state
    // needs a fresh mount to fully clear — simplest correct fix is reloading
    // the chat/documents hooks' state, which a page-level key on sessionId would do.
    window.location.reload();
  };

  const queryDisabled = !sessionId || isStreaming || hasPendingUpload;
  const queryDisabledReason = hasPendingUpload ? "Processing your document..." : undefined;

  if (!ready) {
    return <div className="app-loading">Starting session...</div>;
  }

  if (error || !sessionId) {
    return (
      <div className="app-loading app-error">
        <p>{error || "Something went wrong starting your session."}</p>
        <button className="retry-btn" onClick={retryInit}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <TopBar
        strategy={effectiveStrategy}
        strategyLocked={strategyLocked}
        onStrategyChange={setStrategy}
        onNewChat={handleNewChat}
      />

      <SessionExpiryBanner remainingSeconds={remainingSeconds} isWarning={isWarning} />

      <div className="app-body">
        <button
          className="docs-panel-toggle"
          onClick={() => setDocsPanelOpen((o) => !o)}
          aria-label={docsPanelOpen ? "Close documents panel" : "Open documents panel"}
        >
          <DocumentsPanelToggleIcon size={40} />
        </button>

        <DocumentsPanel open={docsPanelOpen} documents={documents} onUpload={upload} onDelete={remove} />

        <ChatArea
          messages={messages}
          sessionId={sessionId}
          queryDisabled={queryDisabled}
          queryDisabledReason={queryDisabledReason}
          onSend={send}
          onRetry={retryLast}
          onCitationClick={handleCitationClick}
          onBackgroundClick={() => setActiveCitation(null)}
        />

        {activeCitation && (
          <CitationViewer citation={activeCitation} sessionId={sessionId} onClose={() => setActiveCitation(null)} />
        )}
      </div>

      {showPopover && (
        <StrategyPopover
          sessionId={sessionId}
          onChoose={(s) => {
            setStrategy(s);
            setPopoverDismissed(true);
          }}
          onDismiss={() => setPopoverDismissed(true)}
        />
      )}
    </div>
  );
}
