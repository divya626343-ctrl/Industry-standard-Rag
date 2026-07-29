import logging
from fastapi import APIRouter, HTTPException, Response

from Rag_backend.documents.viewer import get_citation_location, get_document_bytes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/citation", tags=["citation"])


@router.get("/{chunk_id}/location")
def citation_location(chunk_id: str, source_collection: str, session_id: str):
    try:
        return get_citation_location(chunk_id, source_collection, session_id)
    except LookupError:
        raise HTTPException(404, "citation not found")
    except PermissionError:
        raise HTTPException(403, "not authorized to view this document")


@router.get("/{chunk_id}/file")
def citation_file(chunk_id: str, source_collection: str, session_id: str):
    try:
        file_bytes, content_type = get_document_bytes(chunk_id, source_collection, session_id)
        return Response(content=file_bytes, media_type=content_type)
    except LookupError:
        raise HTTPException(404, "document not found")
    except PermissionError:
        raise HTTPException(403, "not authorized to view this document")