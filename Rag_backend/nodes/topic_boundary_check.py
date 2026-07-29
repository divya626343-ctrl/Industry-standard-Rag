from Rag_backend.guardrails.topic_boundary import check_topic_boundary, TopicBoundaryResult
import logging
from Rag_backend.graph.state import State
from datetime import timezone, datetime

logger = logging.getLogger(__name__)

def topic_boundary_check(state: State):
    """
    checks whether the rewritten query is in-scope — matches either the
    shared corpus domain or the session's own uploaded document topics
    Reads rewritten_query, session_id
    writes topic_in_scope
    """
    node_name = "topic_boundary_check"
    started_at = datetime.now(timezone.utc)

    logger.info(f"[{node_name}] started | rewritten_query : {state['rewritten_query']}")

    try:
        result: TopicBoundaryResult = check_topic_boundary(
            rewritten_query=state['rewritten_query'],
            session_id=state['session_id'],
        )

        if result.in_scope:
            logger.info(f"[{node_name}] passed | category={result.category}")

            trace_entry = build_trace_entry(
                node=node_name,
                event="passed",
                started_at=started_at,
                details={
                    "in_scope": result.in_scope,
                    "category": result.category,
                }
            )

            return {
                **state,
                "topic_in_scope": result.in_scope,
                "trace_log": state['trace_log'] + [trace_entry],
            }

        logger.info(
            f"[{node_name}] not passed | "
            f"query out of scope | "
            f"routing to end"
        )

        trace_entry = build_trace_entry(
            node=node_name,
            event="not passed",
            started_at=started_at,
            details={
                "reason": result.reason,
                "category": result.category,
                "in_scope": result.in_scope,
            }
        )

        return {
            **state,
            "topic_in_scope": result.in_scope,
            "trace_log": state['trace_log'] + [trace_entry],
            "exit_stage": "topic_boundary",
            "exit_message": "I don't have information about that in the documents I have access to.",
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
            "topic_in_scope": False,
            "trace_log": state['trace_log'] + [trace_entry],
            "exit_stage": "topic_boundary_error",
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