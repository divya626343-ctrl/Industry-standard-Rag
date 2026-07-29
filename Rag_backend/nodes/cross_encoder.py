import logging
from datetime import datetime, timezone
from sentence_transformers import CrossEncoder

from Rag_backend.graph.state import State
from Rag_backend.config.settings import settings

logger = logging.getLogger(__name__)

reranker_model = CrossEncoder(settings.RERANK_MODEL)

def cross_encoder(state: State):

    """
    Reranks fused results(already capped at FUSE_TOP_K , e.g. 20)

    Reads rewritten_query, fused_results
    writes reranked_results
    
    """

    node_name = "cross_encoder"

    started_at = datetime.now(timezone.utc)

    logger.info(f"[{node_name}] started")

    try:

        query = state['rewritten_query']
        candidates = state.get('fused_results') or []

        if not candidates:
            trace_entry = build_trace_entry(
                node=node_name,
                event="success",
                started_at=started_at,
                details={"reranked_count": 0},
            )

            return {
            **state,
            "reranked_results": [],
            "trace_log": state["trace_log"] + [trace_entry],
            }

    

        pairs = [(query, c["payload"]["chunk_text"]) for c in candidates]

        scores = reranker_model.predict(pairs)

        reranked = [
            {
                **candidates, "rerank_score": float(scores)
            }
            for candidates, scores in zip(candidates, scores)
        ]

        reranked.sort(key= lambda c: c["rerank_score"], reverse = True)

        logger.info(f"[{node_name}] success | reranked_count = {len(reranked)}")

        trace_entry = build_trace_entry(
            node = node_name,
            event = "success",
            started_at = started_at,
            details = {"reranked_count" : len(reranked)}
        )

        return {
            **state,
            "reranked_results": reranked,
            "trace_log": state['trace_log'] + [trace_entry]
        }
        
    except Exception as e:
        logger.error(f"[{node_name}] error has occurred | {e}")
        logger.info(f"[{node_name}] falling back to fused results")
 
        trace_entry = build_trace_entry(
            node=node_name,
            event="failed",
            started_at=started_at,
            details={"error": str(e)},
        )
 
        return {
            **state,
            "reranked_results": [],
            "trace_log": state['trace_log'] + [trace_entry],
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
 
