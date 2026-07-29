import logging
from datetime import datetime, timezone

from Rag_backend.graph.state import State
from Rag_backend.config.settings import settings
from Rag_backend.guardrails.answer_relevance import check_answer_relevance

logger = logging.getLogger(__name__)


def answer_relevance_check(state: State):
    """
    Reads generated_answer, rewritten_query, is_fallback_answer, retry_count
    writes relevance_passed, retry_count
    """
    node_name = "answer_relevance_check"
    started_at = datetime.now(timezone.utc)

    if state.get('generation_fallback'):
        logger.info(f"[{node_name}] skipped | fallback answer, passing through")
        trace_entry = build_trace_entry(node=node_name, event="skipped_fallback", started_at=started_at)
        return {
            **state,
            "relevance_passed": True,
            "trace_log": state['trace_log'] + [trace_entry],
        }

    retry_count = state.get('retry_count', 0)
    logger.info(f"[{node_name}] started | retry_count={retry_count}")

    try:
        result = check_answer_relevance(state['rewritten_query'], state['final_answer'])
        passed = result.relevance_score >= settings.ANSWER_RELEVANCE_THRESHOLD

        if passed:
            logger.info(f"[{node_name}] passed | score={result.relevance_score}")
            trace_entry = build_trace_entry(
                node=node_name, event="passed", started_at=started_at,
                details={"score": result.relevance_score},
            )
            return {
                **state,
                "relevance_passed": True,
                "trace_log": state['trace_log'] + [trace_entry],
            }

        retry_count += 1
        logger.info(f"[{node_name}] failed | score={result.relevance_score} | retry_count={retry_count}")

        trace_entry = build_trace_entry(
            node=node_name, event="failed", started_at=started_at,
            details={"score": result.relevance_score, "reason": result.reason, "retry_count": retry_count},
        )

        if retry_count > settings.MAX_GUARDRAIL_RETRIES:
            logger.info(f"[{node_name}] retry cap exceeded, exiting graph")
            return {
                **state,
                "relevance_passed": False,
                "retry_count": retry_count,
                "trace_log": state['trace_log'] + [trace_entry],
                "exit_stage": "relevance_retry_cap_exceeded",
                "exit_message": "I wasn't able to find a confident answer to that in the available documents.",
            }

        return {
            **state,
            "relevance_passed": False,
            "retry_count": retry_count,
            "trace_log": state['trace_log'] + [trace_entry],
            # router reads relevance_passed=False -> loops back to query_rewriter
        }

    except Exception as e:
        logger.error(f"[{node_name}] error has occurred | {e}")
        trace_entry = build_trace_entry(node=node_name, event="error", started_at=started_at, details={"error": str(e)})
        return {
            **state,
            "relevance_passed": None,
            "trace_log": state['trace_log'] + [trace_entry],
            "exit_stage": "answer_relevance_check_error",
            "exit_message": "we ran into an issue processing your request. Please try again."
            
        }


def build_trace_entry(node, event, started_at, details=None):
    completed_at = datetime.now(timezone.utc)
    return {
        "node": node, "event": event,
        "started_at": started_at.isoformat(), "completed_at": completed_at.isoformat(),
        "elapsed_ms": int((completed_at - started_at).total_seconds() * 1000),
        "detail": details or {},
    }