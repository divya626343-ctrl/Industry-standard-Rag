
import hashlib
import logging
import subprocess
import tempfile
from pathlib import Path
import os

import fitz  # pymupdf

from Rag_backend.data_stores.object_store import object_store, build_key

logger = logging.getLogger(__name__)

CONVERTIBLE_FORMATS = {"docx", "pptx"}
PDF_CONTENT_TYPE = "application/pdf"

SOFFICE_CMD = os.environ.get("SOFFICE_PATH", "soffice")
XELATEX_FONT = os.environ.get("XELATEX_FONT", "DejaVu Sans")



def compute_content_hash(file_bytes: bytes) -> str:
   
    return hashlib.sha256(file_bytes).hexdigest()


def convert_to_pdf(file_bytes: bytes, file_format: str) -> bytes:
    """
    Normalizes every supported format into PDF bytes.

    pdf        -> passthrough, no conversion
    docx/pptx  -> libreoffice --headless
    html/md    -> pandoc
    """
    if file_format == "pdf":
        return file_bytes

    if file_format not in CONVERTIBLE_FORMATS:
        raise ValueError(f"[parser] unsupported file_format: {file_format}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        input_path = tmp_dir_path / f"input.{file_format}"
        input_path.write_bytes(file_bytes)

    
        subprocess.run(
                [
                  
                    SOFFICE_CMD, "--headless", "--convert-to", "pdf",
                    "--outdir", str(tmp_dir_path), str(input_path),
                ],
                check=True, capture_output=True,
            )
       
        output_path = tmp_dir_path / "input.pdf"
        if not output_path.exists():
            raise RuntimeError(f"[parser] conversion produced no output for format: {file_format}")

        pdf_bytes = output_path.read_bytes()

    logger.info(f"[parser] converted {file_format} -> pdf ({len(pdf_bytes)} bytes)")
    return pdf_bytes


def extract_elements(pdf_bytes: bytes) -> list[dict]:
    """
    Returns one element per text block, each carrying the
    page number and bounding box needed for citation highlighting later.
    """
    elements = []

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page_number, page in enumerate(doc, start=1):
            blocks = page.get_text("blocks")  # [(x0, y0, x1, y1, text, block_no, block_type), ...]
            for block in blocks:
                x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
                text = text.strip()
                if not text:
                    continue
                elements.append({
                    "text": text,
                    "page_number": page_number,
                    "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                })

    logger.debug(f"[parser] extracted {len(elements)} text blocks")
    return elements


def parse_document(
    file_bytes: bytes,
    file_format: str,
    doc_id: str,
    org: str | None = None,
    content_hash: str | None = None,
    session_id: str | None = None,
) -> dict:
    
    content_hash = content_hash or  compute_content_hash(file_bytes)

    pdf_bytes = convert_to_pdf(file_bytes, file_format)

    storage_key = build_key(doc_id, "document.pdf", org=org, session_id=session_id)
    object_store.upload_file(storage_key, pdf_bytes, PDF_CONTENT_TYPE)

    elements = extract_elements(pdf_bytes)

    return {
        "doc_id": doc_id,
        "content_hash": content_hash,
        "source_file_uri": storage_key,
        "elements": elements,
    }