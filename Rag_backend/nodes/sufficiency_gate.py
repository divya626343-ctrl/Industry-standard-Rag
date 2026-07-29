import logging
from datetime import datetime, timezone

from Rag_backend.graph.state import State
from Rag_backend.config.settings import settings

logger = logging.getLogger(__name__)


def sufficiency_gate(state: State):
    """
    Reads reranked_results, fused_results
    writes sufficient_results
    """
    node_name = "sufficiency_gate"
    started_at = datetime.now(timezone.utc)

    reranked = state.get('reranked_results') or []
    fused = state.get('fused_results') or []
    logger.info(f"[{node_name}] started | reranked_count={len(reranked)} fused_count={len(fused)}")

    try:
        if reranked:
            candidates = [c for c in reranked if c["rerank_score"] >= settings.SUFFICIENCY_SCORE]
            source = "reranked"
        else:
            logger.info(f"[{node_name}] reranked_results empty | falling back to fused_results")
            candidates = fused
            source = "fused_fallback"

        if not candidates:
            logger.info(f"[{node_name}] no candidates survived | source={source}")

            trace_entry = build_trace_entry(
                node=node_name,
                event="insufficient",
                started_at=started_at,
                details={"source": source, "threshold": settings.SUFFICIENCY_SCORE},
            )

            return {
                **state,
                "sufficient_results": [],
                "trace_log": state['trace_log'] + [trace_entry],
                "exit_stage": "sufficiency_gate_no_match",
                "exit_message": "I don't have information about that in the documents I have access to.",
            }

        logger.info(f"[{node_name}] success | source={source} count={len(candidates)}")

        trace_entry = build_trace_entry(
            node=node_name,
            event="success",
            started_at=started_at,
            details={"source": source, "count": len(candidates), "threshold": settings.SUFFICIENCY_SCORE},
        )

        return {
            **state,
            "sufficient_results": candidates,
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
            "sufficient_results": None,
            "trace_log": state['trace_log'] + [trace_entry],
            "exit_stage": "sufficiency_gate_error",
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