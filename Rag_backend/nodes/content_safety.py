from Rag_backend.guardrails.safety import check_safety, SafetyCheckResult
import logging
from Rag_backend.graph.state import State
from datetime import timezone, datetime

logger = logging.getLogger(__name__)

def content_safety(state: State):

    """
    checks whether the asked query is safe 
    Reads rewritten query 
    writes safety
    
    """
    node_name = "content_safety"
    started_at = datetime.now(timezone.utc)

    logger.info(f"[{node_name}] started | rewritten_query : {state['rewritten_query']}")

    try:

        result : SafetyCheckResult = check_safety(rewritten_query=state['rewritten_query'])

        if result.is_safe:
            logger.info(f"[{node_name}] passed , rewritten query is totally safe")

            trace_entry = build_trace_entry(
                node = node_name,
                event = "passed",
                started_at = started_at,
                details = {
                    "is_safe" : result.is_safe,
                    "category": result.category
                }
            )

            return {
                **state,
                "safety": result.is_safe,
                "trace_log": state['trace_log'] + [trace_entry]
            }
        
        logger.info(
            f"[{node_name}] not passed  |"
            f"overall rewritten query was not safe |"
            f"routing to end"
        )
            

        trace_entry = build_trace_entry(
            node = node_name,
            event = "not passed",
            started_at = started_at,
            details = {
                "reason" : result.reason,
                "category": result.category,
                "is_safe" : result.is_safe
            }
        )

        return {
            **state,
            "safety": result.is_safe,
            "trace_log" : state['trace_log'] + [trace_entry] , 
            "exit_stage": "safety_check_error",
            "exit_message": "I can't help with that request."
        }
    

    except Exception as e:
        logger.error(f"[{node_name}] error has occured {e}")

        trace_entry = build_trace_entry(
            node = node_name,
            event = 'failed',
            started_at = started_at,
            details = {
                "error": str(e)
            }
        )

        return {
            **state,
            "safety" : False,
            "trace_log": state['trace_log'] + [trace_entry],
            "exit_stage": "safety_check_error",
            "exit_message": "we ran into an issue processing your request. Please try again."
        }



def build_trace_entry(
    node: str,
    event: str,
    started_at: datetime,
    details: dict | None = None,
) -> dict:
    completed_at = datetime.now(timezone.utc)
    return {
        "node":         node,
        "event":        event,
        "started_at":   started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "elapsed_ms":   int((completed_at - started_at).total_seconds() * 1000),
        "detail":       details or {},
    }