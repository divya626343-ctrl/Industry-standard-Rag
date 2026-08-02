import { useCallback, useRef, useState } from "react";
import { getTaskStatus, uploadDocument } from "../api/upload";
import { deleteDocument } from "../api/documents";
import type { DocumentItem } from "../types";
import { ApiError } from "../api/client";

export function useDocuments(sessionId: string | null, strategy: string | null, onUploadStarted?: () => void) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const pollTimers = useRef<Record<string, number>>({});

  const pollStatus = useCallback((taskId: string) => {
    const tick = async () => {
      try {
        const status = await getTaskStatus(taskId);

        setDocuments((prev) =>
          prev.map((d) => {
            if (d.taskId !== taskId) return d;
            if (status.state === "SUCCESS") {
              return { ...d, status: "indexed", docId: status.result?.doc_id };
            }
            if (status.state === "FAILURE") {
              return { ...d, status: "failed", error: status.error || "Indexing failed." };
            }
            return { ...d, status: status.state === "STARTED" ? "processing" : "queued" };
          }),
        );

        if (status.state === "SUCCESS" || status.state === "FAILURE") {
          window.clearTimeout(pollTimers.current[taskId]);
          delete pollTimers.current[taskId];
          return;
        }
      } catch (e) {
        console.error("task-status poll failed", e);
      }
      pollTimers.current[taskId] = window.setTimeout(tick, 1500);
    };
    tick();
  }, []);

  const upload = useCallback(
    async (file: File) => {
      if (!sessionId) return;
      onUploadStarted?.();

      const tempId = `pending-${Date.now()}-${file.name}`;
      setDocuments((prev) => [...prev, { id: tempId, taskId: tempId, filename: file.name, status: "queued" }]);

      try {
        const res = await uploadDocument(file, sessionId, strategy);

        if (res.status === "duplicate") {
          setDocuments((prev) =>
            prev.map((d) => (d.id === tempId ? { ...d, status: "failed", error: "You've already uploaded this file." } : d)),
          );
          return;
        }

        const taskId = res.task_id as string;
        setDocuments((prev) => prev.map((d) => (d.id === tempId ? { ...d, id: taskId, taskId, status: "queued" } : d)));
        pollStatus(taskId);
      } catch (e) {
        const message =
          e instanceof ApiError && e.status === 413
            ? "File is too large."
            : e instanceof ApiError && e.status === 400
              ? "Unsupported file type."
              : "Upload failed.";
        setDocuments((prev) => prev.map((d) => (d.id === tempId ? { ...d, status: "failed", error: message } : d)));
      }
    },
    [sessionId, strategy, pollStatus, onUploadStarted],
  );

  const retry = useCallback(
    async (doc: DocumentItem, file: File) => {
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
      await upload(file);
    },
    [upload],
  );

  // Only ever called from UI that already gates on status === "indexed" | "failed" —
  // enforced again here as a second guard, not just a UI-layer assumption.
  const remove = useCallback(
    async (doc: DocumentItem) => {
      if (!sessionId || (doc.status !== "indexed" && doc.status !== "failed")) return;
      const snapshot = documents;
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
      if (!doc.docId) return; // failed docs never got a doc_id, nothing to delete server-side
      try {
        await deleteDocument(doc.docId, sessionId);
      } catch (e) {
        console.error("delete failed, reverting", e);
        setDocuments(snapshot);
      }
    },
    [documents, sessionId],
  );

  const hasPendingUpload = documents.some((d) => d.status === "queued" || d.status === "processing");

  return { documents, upload, retry, remove, hasPendingUpload };
}
