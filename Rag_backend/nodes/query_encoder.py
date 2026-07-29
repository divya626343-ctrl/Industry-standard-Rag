import logging
from datetime import datetime, timezone

from Rag_backend.graph.state import State
from Rag_backend.pipeline.ingestion.embedder import dense_model, sparse_model

logger = logging.getLogger(__name__)


def query_encode(state: State):
    """
    Encodes rewritten_query into dense + sparse vectors, using the SAME
    model instances embedder.py used at ingestion time — required so the
    query and the indexed chunks share one embedding/vocabulary space.
    Reads rewritten_query
    writes dense_query_vector, sparse_query_vector
    """
    node_name = "query_encode"
    started_at = datetime.now(timezone.utc)

    logger.info(f"[{node_name}] started | rewritten_query : {state['rewritten_query']}")

    try:
        query_text = state['rewritten_query']

        dense_vector = list(dense_model.embed([query_text]))[0].tolist()

        sparse_result = list(sparse_model.embed([query_text]))[0]
        sparse_vector = {
            idx: val
            for idx, val in zip(sparse_result.indices.tolist(), sparse_result.values.tolist())
        }

        logger.info(f"[{node_name}] success | dense_dim={len(dense_vector)} sparse_terms={len(sparse_vector)}")

        trace_entry = build_trace_entry(
            node=node_name,
            event="success",
            started_at=started_at,
            details={
                "dense_dim": len(dense_vector),
                "sparse_terms": len(sparse_vector),
            }
        )

        return {
            **state,
            "dense_query_vector": dense_vector,
            "sparse_query_vector": sparse_vector,
            "trace_log": state['trace_log'] + [trace_entry],
        }

    except Exception as e:
        logger.error(f"[{node_name}] error has occurred | {e}")

        trace_entry = build_trace_entry(
            node=node_name,
            event="failed",
            started_at=started_at,
            details={"error": str(e)}
        )

        return {
            **state,
            "dense_query_vector": None,
            "sparse_query_vector": None,
            "trace_log": state['trace_log'] + [trace_entry],
            "exit_stage": "query_encode_error",
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