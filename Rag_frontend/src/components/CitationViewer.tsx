import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import type { PDFDocumentProxy } from "pdfjs-dist";
import { getCitationFileBlob, getCitationLocation } from "../api/citation";
import { CloseIcon, CircleChevronIcon } from "./icons/icons";
import type { Citation } from "../types";

pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;

interface Props {
  citation: Citation;
  sessionId: string;
  onClose: () => void;
}

interface HighlightRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export function CitationViewer({ citation, sessionId, onClose }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pdfRef = useRef<PDFDocumentProxy | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  const [loadingLocation, setLoadingLocation] = useState(true);
  const [loadingFile, setLoadingFile] = useState(false);
  const [errorState, setErrorState] = useState<"not-found" | "not-authorized" | "generic" | null>(null);
  const [citedPage, setCitedPage] = useState<number | null>(null);
  const [bbox, setBbox] = useState<[number, number, number, number] | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageCount, setPageCount] = useState<number | null>(null);
  const [docLabel, setDocLabel] = useState<string>("");
  const [highlightRect, setHighlightRect] = useState<HighlightRect | null>(null);

  // Step 1: fast metadata lookup — panel opens on this alone.
  useEffect(() => {
    let cancelled = false;
    setLoadingLocation(true);
    setErrorState(null);

    getCitationLocation(citation.chunk_id, citation.source_collection, sessionId)
      .then((loc) => {
        if (cancelled) return;
        setCitedPage(loc.page_number);
        setCurrentPage(loc.page_number);
        setBbox(loc.bbox);
        setDocLabel(loc.source_file_uri.split("/").pop() || loc.doc_id);
        setLoadingLocation(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setErrorState(e?.status === 404 ? "not-found" : e?.status === 403 ? "not-authorized" : "generic");
        setLoadingLocation(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [citation.chunk_id]);

  // Step 2: heavier file fetch, only once the panel/location is settled.
  useEffect(() => {
    if (loadingLocation || errorState) return;
    let cancelled = false;
    setLoadingFile(true);

    getCitationFileBlob(citation.chunk_id, citation.source_collection, sessionId)
      .then(async (blob) => {
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        objectUrlRef.current = url;
        const pdf = await pdfjsLib.getDocument(url).promise;
        if (cancelled) return;
        pdfRef.current = pdf;
        setPageCount(pdf.numPages);
        setLoadingFile(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setErrorState(e?.status === 404 ? "not-found" : e?.status === 403 ? "not-authorized" : "generic");
        setLoadingFile(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadingLocation, errorState, citation.chunk_id]);

  // Render current page + compute highlight rect (only drawn when on the cited page).
  useEffect(() => {
    const pdf = pdfRef.current;
    const canvas = canvasRef.current;
    if (!pdf || !canvas) return;

    let cancelled = false;

    (async () => {
      const page = await pdf.getPage(currentPage);
      const viewport = page.getViewport({ scale: 1.4 });
      const context = canvas.getContext("2d");
      if (!context || cancelled) return;

      canvas.width = viewport.width;
      canvas.height = viewport.height;
      await page.render({ canvasContext: context, viewport }).promise;
      if (cancelled) return;

      if (bbox && citedPage === currentPage) {
        // convertToViewportRectangle handles PDF's bottom-up coordinate space
        // and any page rotation correctly -- safer than hand-rolling the flip math.
        const [vx0, vy0, vx1, vy1] = viewport.convertToViewportRectangle(bbox);
        setHighlightRect({
          left: Math.min(vx0, vx1),
          top: Math.min(vy0, vy1),
          width: Math.abs(vx1 - vx0),
          height: Math.abs(vy1 - vy0),
        });
      } else {
        setHighlightRect(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [currentPage, bbox, citedPage, pageCount]);

  useEffect(() => {
    return () => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
      pdfRef.current?.destroy();
    };
  }, []);

  return (
    <aside className="citation-panel">
      <div className="citation-panel-header">
        <span className="citation-panel-title" title={docLabel}>
          {docLabel} {citedPage ? `— p.${citedPage}` : ""}
        </span>
        <button className="citation-panel-close" onClick={onClose} aria-label="Close viewer">
          <CloseIcon />
        </button>
      </div>

      <div className="citation-panel-body">
        {loadingLocation && <p className="citation-loading">Locating citation...</p>}

        {errorState === "not-found" && <p className="citation-error">This document is no longer available.</p>}
        {errorState === "not-authorized" && <p className="citation-error">You're not authorized to view this document.</p>}
        {errorState === "generic" && <p className="citation-error">Something went wrong loading this citation.</p>}

        {!loadingLocation && !errorState && (
          <>
            {loadingFile && <p className="citation-loading">Loading document...</p>}
            <div className="citation-canvas-wrap" style={{ position: "relative" }}>
              <canvas ref={canvasRef} style={{ maxWidth: "100%", display: loadingFile ? "none" : "block" }} />
              {highlightRect && !loadingFile && (
                <div
                  className="citation-highlight"
                  style={{
                    position: "absolute",
                    left: highlightRect.left,
                    top: highlightRect.top,
                    width: highlightRect.width,
                    height: highlightRect.height,
                  }}
                />
              )}
            </div>
          </>
        )}
      </div>

      {pageCount && !errorState && (
        <div className="citation-pagination">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
            aria-label="Previous page"
          >
            <CircleChevronIcon size={26} style={{ transform: "rotate(180deg)" }} />
          </button>
          <span>
            Page {currentPage} of {pageCount}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(pageCount, p + 1))}
            disabled={currentPage >= pageCount}
            aria-label="Next page"
          >
            <CircleChevronIcon size={26} />
          </button>
        </div>
      )}
    </aside>
  );
}
