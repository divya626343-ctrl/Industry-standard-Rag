import logging
from datetime import datetime, timezone

from Rag_backend.graph.state import State
from Rag_backend.data_stores.qdrant_store import vector_store
from Rag_backend.data_stores.redis_store import collection_name

logger = logging.getLogger(__name__)


def retriever(state: State):
    """
   
    Reads dense_query_vector, sparse_query_vector, session_id
    writes  main_corpus_results, session_results
    """
    node_name = "retrieve"
    started_at = datetime.now(timezone.utc)

    logger.info(f"[{node_name}] started | session_id={state.get('session_id')}")

    try:
        dense_vector = state['dense_query_vector']
        sparse_vector = state['sparse_query_vector']
        session_id = state.get('session_id')

        shared_hits = vector_store.search_hybrid(
            collection_name=collection_name(),  # shared/main corpus
            dense_query_vector=dense_vector,
            sparse_query_vector=sparse_vector,
        )
        for hit in shared_hits:
            hit["source_collection"] = "shared"

        session_hits = []
        if session_id:
            session_hits = vector_store.search_hybrid(
                collection_name=collection_name(session_id),
                dense_query_vector=dense_vector,
                sparse_query_vector=sparse_vector,
            )
            for hit in session_hits:
                hit["source_collection"] = "session"

        logger.info(
            f"[{node_name}] success | shared_hits={len(shared_hits)} session_hits={len(session_hits)}"
        )

        trace_entry = build_trace_entry(
            node=node_name,
            event="success",
            started_at=started_at,
            details={"shared_hits": len(shared_hits), "session_hits": len(session_hits)},
        )

        return {
            **state,
            "main_corpus_results": shared_hits,
            "session_results": session_hits,
            "trace_log": state['trace_log'] + [trace_entry],
        }

    except Exception as e:
        logger.error(f"[{node_name}] error has occurred | {e}")

        trace_entry = build_trace_entry(
            node=node_name,
            event="failed",
            started_at=started_at,
            details={"error": str(e)},
        )

        return {
            **state,
            "main_corpus_results": None,
            "session_results": None,
            "trace_log": state['trace_log'] + [trace_entry],
            "exit_stage": "retrieve_error",
            "exit_message": "we ran into an issue processing your request. Please try again.",
        }


def build_trace_entry(
    node: str,
    event: str,
    started_at: datetime,
    details: dict | None = None,
) -> dict:
    completed_at = datetime.now(timezone.utc)
    return {
        "node": node,
        "event": event,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "elapsed_ms": int((completed_at - started_at).total_seconds() * 1000),
        "detail": details or {},
    }