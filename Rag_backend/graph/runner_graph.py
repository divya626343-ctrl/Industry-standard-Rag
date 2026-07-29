import logging
from Rag_backend.graph.build_graph import build_graph
from Rag_backend.graph.state import create_initial_state
from Rag_backend.data_stores.redis_store import redis_store

logger = logging.getLogger(__name__)


graph = None

def get_graph():
    global graph
    if graph is None:
        graph = build_graph()
    return graph

def run_query(query: str, session_id: str)-> dict:
    """
    entry point called by the FastAPI query route
    
    """
    redis_store.heartbeat(session_id)

    initial_state = create_initial_state(session_id=session_id, query=query)

    config = {"configurable": {"thread_id": session_id}}

    try:
        result_state = get_graph().invoke(initial_state, config = config)
    except Exception as e:

        logger.error(f"[runner_graph] graph invocation failed | session_id = {session_id} | {e}")
        return {
            "answer": "we ran into an issue processing your request. Please try again.",
            "citations": {},
            "exit_stage": "graph_invocation_error",
        }
    
    redis_store.append_turn(session_id, "user", query)

    if result_state.get("exit_stage"):
        logger.info(f"[runner_graph] session_id={session_id} exited at {result_state['exit_stage']}")
        answer = result_state.get("exit_message") or "I couldn't process that request."
        redis_store.append_turn(session_id, "assistant", answer)
        return {
            "answer": answer,
            "citations": {},
            "exit_stage": result_state["exit_stage"],
        }
 
    answer = result_state.get("final_answer") or "I couldn't generate an answer."
    redis_store.append_turn(session_id, "assistant", answer)
 
    return {
        "answer": answer,
        "citations": result_state.get("citations") or {},
        "exit_stage": None,
    }