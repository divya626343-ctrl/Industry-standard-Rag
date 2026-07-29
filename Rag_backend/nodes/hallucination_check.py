import logging
from datetime import datetime, timezone

from Rag_backend.graph.state import State
from Rag_backend.config.settings import settings
from Rag_backend.guardrails.hallucination import check_hallucination

logger = logging.getLogger(__name__)


def hallucination_check(state: State):
    """
    Reads generated_answer, sufficient_results, is_fallback_answer, retry_count
    writes hallucination_passed, retry_count

    """
    node_name = "hallucination_check"
    started_at = datetime.now(timezone.utc)

    if state.get('generation_fallback'):
        logger.info(f"[{node_name}] skipped | fallback answer, passing through")

        trace_entry = build_trace_entry(
            node=node_name, event="skipped_fallback", started_at=started_at,
        )

        return {
            **state,
            "hallucination_passed": True,
            "trace_log": state['trace_log'] + [trace_entry],
        }

    retry_count = state.get('retry_count', 0)
    logger.info(f"[{node_name}] started | retry_count={retry_count}")

    try:
        result = check_hallucination(
            query=state['rewritten_query'],
            answer=state['draft_answer'],
            context_chunks=state.get('sufficient_results') or [],
        )

        if result.is_faithful:
            logger.info(f"[{node_name}] passed")

            trace_entry = build_trace_entry(
                node=node_name, event="passed", started_at=started_at,
                details={"category": result.category},
            )

            return {
                **state,
                "hallucination_passed": True,
                "trace_log": state['trace_log'] + [trace_entry],
            }

        
        retry_count += 1
        logger.info(f"[{node_name}] failed | category={result.category} | retry_count={retry_count}")

        trace_entry = build_trace_entry(
            node=node_name, event="failed", started_at=started_at,
            details={"category": result.category, "reason": result.reason, "retry_count": retry_count},
        )

        if retry_count > settings.MAX_GUARDRAIL_RETRIES:
            logger.info(f"[{node_name}] retry cap exceeded, exiting graph")
            return {
                **state,
                "hallucination_passed": False,
                "retry_count": retry_count,
                "trace_log": state['trace_log'] + [trace_entry],
                "exit_stage": "hallucination_retry_cap_exceeded",
                "exit_message": "I wasn't able to generate a confident, fully grounded answer to that.",
            }

        return {
            **state,
            "hallucination_passed": False,
            "retry_count": retry_count,
            "trace_log": state['trace_log'] + [trace_entry],
            # no exit_stage set — router reads hallucination_passed=False and loops back to generation
        }

    except Exception as e:
        logger.error(f"[{node_name}] error has occurred | {e}")

        trace_entry = build_trace_entry(
            node=node_name, event="error", started_at=started_at,
            details={"error": str(e)},
        )

        return {
            **state,
            "hallucination_passed": None,
            "trace_log": state['trace_log'] + [trace_entry],
            "exit_stage": "hallucination_check_error",
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