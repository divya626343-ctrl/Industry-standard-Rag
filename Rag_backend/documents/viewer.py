
import logging
from Rag_backend.data_stores.object_store import object_store
from Rag_backend.data_stores.qdrant_store import vector_store
from Rag_backend.data_stores.redis_store import collection_name, redis_store

logger = logging.getLogger(__name__)

PDF_CONTENT_TYPE = "application/pdf"  

def check_scope(session_id: str, source_collection: str, source_file_uri: str) -> bool:
    """
    Shared-corpus chunks are accessible to anyone. Session-uploaded chunks
    are only accessible to the session that owns them
    """
    if source_collection == "shared":
        return True

    if source_collection == "session":
        parts = source_file_uri.split("/")
        owning_session_id = parts[1] if len(parts) > 1 else None
        return owning_session_id == session_id

    logger.warning(f"[viewer] unknown source_collection: {source_collection}")
    return False


def resolve_payload(chunk_id: str, source_collection: str, session_id: str) -> dict:
    """Fetches the chunk's Qdrant payload and enforces the scope check.
    Internal — callers use get_citation_location / get_document_bytes."""
    resolved_collection = collection_name(session_id if source_collection == "session" else None)
    payload = vector_store.get_chunk_payload(chunk_id, resolved_collection)

    if payload is None:
        raise LookupError(f"chunk {chunk_id} not found in {resolved_collection}")

    if not check_scope(session_id, source_collection, payload["source_file_uri"]):
        logger.warning(
            f"[viewer] scope check failed | session_id={session_id} "
            f"chunk_id={chunk_id} source_collection={source_collection}"
        )
        raise PermissionError(f"session {session_id} cannot access chunk {chunk_id}")

    return payload



def get_citation_location(chunk_id: str, source_collection: str, session_id: str) -> dict:
    """Fetches page_number/bbox/source_file_uri for a citation — no file bytes."""
    payload = resolve_payload(chunk_id, source_collection, session_id)

    logger.info(
        f"[viewer] location resolved | chunk_id={chunk_id} "
        f"doc_id={payload['doc_id']} page={payload['page_number']}"
    )

    return {
        "doc_id": payload["doc_id"],
        "source_file_uri": payload["source_file_uri"],
        "page_number": payload["page_number"],
        "bbox": payload["bbox"],
    }

def get_document_bytes(chunk_id: str, source_collection: str, session_id: str) -> tuple[bytes, str]:
    """Resolves + scope-checks the chunk, then fetches the PDF bytes.
    Returns (bytes, content_type) so the FastAPI route can set the response header directly."""
    payload = resolve_payload(chunk_id, source_collection, session_id)
    file_bytes = object_store.get_file(payload["source_file_uri"])

    logger.info(
        f"[viewer] served file bytes | chunk_id={chunk_id} "
        f"doc_id={payload['doc_id']} bytes={len(file_bytes)}"
    )

    return file_bytes, PDF_CONTENT_TYPE

def get_citation_bundle(chuck_id, source_collection, session_id):
    location = get_citation_location(chunk_id=chuck_id, source_collection=source_collection, session_id=session_id)
    file_bytes , content_type = get_document_bytes(chunk_id= chuck_id, source_collection=source_collection, session_id=session_id)
    return {**location, "file_bytes": file_bytes, "content_type": content_type}



def delete_document(doc_id: str, session_id: str) -> None:
    target_collection = collection_name(session_id)

    payload = vector_store.get_payload_by_doc_id(target_collection, doc_id)
    if payload is None:
        raise LookupError(f"doc_id {doc_id} not found in {target_collection}")

    vector_store.delete_points_by_doc_id(target_collection, doc_id)
    object_store.delete_file(payload["source_file_uri"])
    redis_store.remove_doc_topic_summary(session_id, doc_id)
    redis_store.remove_content_hash(session_id, payload["content_hash"])

    logger.info(f"[viewer] deleted document | doc_id={doc_id} session_id={session_id}")