import logging
from datetime import datetime, timezone

from Rag_backend.graph.state import State
from Rag_backend.config.settings import settings

logger = logging.getLogger(__name__)



def rrf_scores(results: list[dict]) -> dict[str, float]:
    """
    Rank-based RRF contribution for one collection's result list.
    """
    return {
        hit["chunk_id"]: 1 / (settings.RRF_K + rank + 1)
        for rank, hit in enumerate(results)
    }


def fuse(state: State):
    """
    Level-2 fusion: combines the main-corpus and session-collection
    result lists 
    Reads main_corpus_results, session_results
    writes fused_results
    """
    node_name = "fuse"
    started_at = datetime.now(timezone.utc)

    logger.info(f"[{node_name}] started")

    try:
        shared_results = state.get('main_corpus_results') or []
        session_results = state.get('session_results') or []

        shared_scores = rrf_scores(shared_results)
        session_scores = rrf_scores(session_results)

        by_chunk_id = {hit["chunk_id"]: hit for hit in shared_results + session_results}

        combined_scores: dict[str, float] = {}
        for chunk_id, score in shared_scores.items():
            combined_scores[chunk_id] = combined_scores.get(chunk_id, 0) + score
        for chunk_id, score in session_scores.items():
            combined_scores[chunk_id] = combined_scores.get(chunk_id, 0) + score

        ranked_chunk_ids = sorted(combined_scores, key=combined_scores.get, reverse=True)

        fused_results = []
        for chunk_id in ranked_chunk_ids[:settings.FUSE_TOP_K]:
            hit = by_chunk_id[chunk_id]
            fused_results.append({
                "chunk_id": chunk_id,
                "rrf_score": combined_scores[chunk_id],
                "source_collection": hit["source_collection"],
                "payload": hit["payload"],
            })

        logger.info(f"[{node_name}] success | fused_count={len(fused_results)}")

        trace_entry = build_trace_entry(
            node=node_name,
            event="success",
            started_at=started_at,
            details={"fused_count": len(fused_results)},
        )

        return {
            **state,
            "fused_results": fused_results,
            "trace_log": state['trace_log'] + [trace_entry],
        }

    except Exception as e:
        logger.error(f"[{node_name}] error has occurred | continuing with fallback | {e}")

        # failure here shouldn't stop the pipeline. Fall back to whichever
        # raw result list is available, unranked, so sufficiency_gate still
        
        fallback_results = (state.get('main_corpus_results') or []) + (state.get('session_results') or [])
        fallback_results = [
            {
                "chunk_id": hit["chunk_id"],
                "rrf_score": 0.0,
                "source_collection": hit["source_collection"],
                "payload": hit["payload"],
            }
            for hit in fallback_results[:settings.FUSE_TOP_K]
        ]

        trace_entry = build_trace_entry(
            node=node_name,
            event="failed_continued",
            started_at=started_at,
            details={"error": str(e), "fallback_count": len(fallback_results)},
        )

        return {
            **state,
            "fused_results": fallback_results,
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