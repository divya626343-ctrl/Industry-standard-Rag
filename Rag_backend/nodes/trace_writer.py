import logging
from datetime import datetime, timezone

from Rag_backend.graph.state import State
from Rag_backend.data_stores.redis_store import redis_store

logger = logging.getLogger(__name__)


def trace_writer(state: State):
    """
    Reads trace_log, session_id, exit_stage
    writes nothing new to state (pass-through), persists to Redis as a
    side effect
    """
    node_name = "trace_writer"


    session_id = state.get('session_id')
    trace_log = state.get('trace_log') or []

    try:
        if session_id:
            for entry in trace_log:
                redis_store.append_trace(session_id, entry)

        logger.info(
            f"[{node_name}] persisted {len(trace_log)} trace entries | "
            f"session_id={session_id} | exit_stage={state.get('exit_stage', 'completed')}"
        )

    except Exception as e:
       
        logger.error(f"[{node_name}] failed to persist trace | {e}")

    return state