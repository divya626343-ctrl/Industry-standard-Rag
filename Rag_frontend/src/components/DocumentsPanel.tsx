import { useRef } from "react";
import type { DocumentItem } from "../types";
import { DeleteIcon, BareArrowUpIcon } from "./icons/icons";

interface Props {
  open: boolean;
  documents: DocumentItem[];
  onUpload: (file: File) => void;
  onDelete: (doc: DocumentItem) => void;
}

const ACCEPTED = ".pdf,.html,.htm,.md";

function StatusPill({ status }: { status: DocumentItem["status"] }) {
  const map: Record<DocumentItem["status"], { label: string; className: string }> = {
    queued: { label: "Queued", className: "pill pill-info" },
    processing: { label: "Processing", className: "pill pill-info" },
    indexed: { label: "Indexed", className: "pill pill-success" },
    failed: { label: "Failed", className: "pill pill-error" },
  };
  const m = map[status];
  return <span className={m.className}>{m.label}</span>;
}

export function DocumentsPanel({ open, documents, onUpload, onDelete }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!open) return null;

  return (
    <aside className="documents-panel">
      <p className="panel-label">Documents</p>

      <div className="documents-list">
        {documents.length === 0 && <p className="documents-empty">No documents uploaded yet.</p>}
        {documents.map((doc) => {
          const canDelete = doc.status === "indexed" || doc.status === "failed";
          return (
            <div key={doc.id} className="document-row">
              <div className="document-row-main">
                <span className="document-filename" title={doc.filename}>
                  {doc.filename}
                </span>
                <StatusPill status={doc.status} />
              </div>
              {doc.error && <p className="document-error-text">{doc.error}</p>}
              {canDelete && (
                <button
                  className="document-delete-btn"
                  onClick={() => onDelete(doc)}
                  aria-label={`Delete ${doc.filename}`}
                  title="Delete document"
                >
                  <DeleteIcon size={20} />
                </button>
              )}
            </div>
          );
        })}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED}
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onUpload(file);
          e.target.value = "";
        }}
      />
      <button className="upload-btn" onClick={() => fileInputRef.current?.click()}>
        <span>Upload</span>
        <BareArrowUpIcon size={16} style={{ marginLeft: 8 }} />
      </button>
      <p className="upload-hint">pdf, html, md</p>
    </aside>
  );
}
