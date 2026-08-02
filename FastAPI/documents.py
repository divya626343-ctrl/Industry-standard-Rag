import logging
from fastapi import APIRouter, HTTPException, Response

from Rag_backend.documents.viewer import get_citation_location, get_document_bytes, delete_document

logger = logging.getLogger(__name__)

citation_router = APIRouter(prefix="/citation", tags=["citation"])
documents_router = APIRouter(prefix="/documents", tags=["documents"])


@citation_router.get("/{chunk_id}/location")
def citation_location(chunk_id: str, source_collection: str, session_id: str):
    try:
        return get_citation_location(chunk_id, source_collection, session_id)
    except LookupError:
        raise HTTPException(404, "citation not found")
    except PermissionError:
        raise HTTPException(403, "not authorized to view this document")


@citation_router.get("/{chunk_id}/file")
def citation_file(chunk_id: str, source_collection: str, session_id: str):
    try:
        file_bytes, content_type = get_document_bytes(chunk_id, source_collection, session_id)
        return Response(content=file_bytes, media_type=content_type)
    except LookupError:
        raise HTTPException(404, "document not found")
    except PermissionError:
        raise HTTPException(403, "not authorized to view this document")


@documents_router.delete("/{doc_id}")
def delete_document_route(doc_id: str, session_id: str):
    try:
        delete_document(doc_id, session_id)
    except LookupError:
        raise HTTPException(404, "document not found")
    except Exception as e:
        logger.error(f"[documents] delete failed | doc_id={doc_id} session_id={session_id} | {e}")
        raise HTTPException(500, "failed to delete document")

    return {"status": "deleted", "doc_id": doc_id}