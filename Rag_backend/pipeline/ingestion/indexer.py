import logging
import time
import uuid

from Rag_backend.pipeline.ingestion.parser import parse_document, compute_content_hash
from Rag_backend.pipeline.ingestion.chunker import chunk_elements
from Rag_backend.pipeline.ingestion.embedder import embed_chunks
from Rag_backend.data_stores.qdrant_store import vector_store
from Rag_backend.data_stores.redis_store import redis_store, collection_name
from Rag_backend.llm_client import call_llm_raw, TaskType
from Rag_backend.config.prompts import SUMMARY_GENERATION_PROMPT


logger = logging.getLogger(__name__)

def generate_doc_summary(elements: list[dict]) -> str:
    preview_text = " ".join(e["text"] for e in elements[:20]) 
    return call_llm_raw(
        prompt=f"document to be summarized:\n{preview_text}",
        system=SUMMARY_GENERATION_PROMPT,
        task= TaskType.JUDGE,
        temperature=0.0,
    )

def ingest_document(
    file_bytes: bytes,
    file_format: str,
    filename: str,
    org: str | None = None,
    session_id: str | None = None,
    chosen_strategy: str | None = None,
) -> dict:
    """full ingestion pipeline : parse chunk embed and persist
    Qdrant + Redis called by the celery ingestion task
    """

    content_hash = compute_content_hash(file_bytes=file_bytes)

    if session_id and redis_store.has_content_hash(session_id, content_hash):
       logger.info(f"[indexer] duplicate upload skipped | session_id={session_id} content_hash={content_hash}")
       return {"doc_id": None, "chunks_indexed": 0, "strategy": None, "status": "duplicate"}

    doc_id = str(uuid.uuid4())

    parsed = parse_document(file_bytes, file_format, doc_id, org=org, session_id = session_id, content_hash=content_hash)

    chunks, strategy_name = chunk_elements(
    parsed["elements"],
    chosen_strategy,
    session_id,
)
    embeddings = embed_chunks(chunks)

    collection = collection_name(session_id)

    if not vector_store.collection_exists(collection):
        vector_store.create_collection(collection, dense_vector_size= 384)

    payloads = [{
        "doc_id": doc_id,
        "chunk_index": c["chunk_index"],
        "chunk_text": c["text"],
        "page_number": c["page_number"],
        "bbox": c["bbox"],
        "org": org,
        "doc_title": filename,
        "file_format": file_format,
        "source_collection": "session" if session_id else "shared",
        "session_id": session_id,
        "source_file_uri": parsed["source_file_uri"],
        "content_hash": parsed["content_hash"],
        "ingested_at": time.time(),
    } for c in chunks]

    vector_store.upsert_chunks(
        collection_name= collection,
        chunk_ids=[c["chunk_id"] for c in chunks],
        dense_vectors=[e["dense"] for e in embeddings],
        sparse_vectors = [e["sparse"] for e in embeddings],
        payloads=payloads
    )

    if session_id:
        redis_store.set_active_chunking_strategy(session_id, strategy_name)
        redis_store.add_content_hash(session_id, content_hash)
        summary = generate_doc_summary(parsed["elements"])
        redis_store.add_doc_topic_summary(session_id, doc_id, summary) 
        logger.info(f"[indexer] session={session_id} doc_summary stored")
 
    logger.info(f"[indexer] doc_id={doc_id} indexed, {len(chunks)} chunks, strategy={strategy_name}")
 
    return {"doc_id": doc_id, "chunks_indexed": len(chunks), "strategy": strategy_name}
 