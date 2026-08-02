import logging
from Rag_backend.data_stores.redis_store import redis_store
from Rag_backend.graph.state import create_initial_state
from Rag_backend.graph.build_graph import build_graph_async

_async_graph = None

async def get_async_graph():
    global _async_graph
    if _async_graph is None:
        _async_graph = await build_graph_async()
    return _async_graph

logger = logging.getLogger(__name__)

NODE_MESSAGES = {
   "rewrite_query": "Understanding your question...",
    "topic_boundary_check": "Checking if this is in scope...",
    "retriever": "Searching documents...",
    "cross_encoder": "Ranking results...",
    "sufficiency_gate": "Evaluating context...",
    "hallucination_check": "Double-checking the answer...",
    "answer_relevance_check": "Double-checking the answer...",
    # safety_check intentionally omitted → silent
}

async def run_query_streaming(query: str, session_id: str):
    """
    Async generator entry point for the SSE route.
    Yields dicts; caller (FastAPI route) serializes to SSE.
    """
    redis_store.heartbeat(session_id)
    redis_store.append_turn(session_id, "user", query)

    initial_state = create_initial_state(session_id=session_id, query=query)
    config = {"configurable": {"thread_id": session_id}}

    final_answer_parts = []
    exit_stage = None
    exit_message = None
    citations = {}
    latest_trace_log = []  # accumulates the full trace as nodes run

    try:
        async for stream_mode, chunk in (await get_async_graph()).astream(
            initial_state, config=config, stream_mode=["updates", "messages"]
        ):
            if stream_mode == "updates":
                node_name = list(chunk.keys())[0]
                node_output = chunk[node_name]

                if node_output.get("trace_log"):
                    latest_trace_log = node_output["trace_log"]  # always the full log so far

                if node_name in NODE_MESSAGES:
                    yield {"type": "status", "node": node_name, "message": NODE_MESSAGES[node_name]}

                if node_output.get("exit_stage"):
                    exit_stage = node_output["exit_stage"]
                    exit_message = node_output.get("exit_message") or "I couldn't process that request."

                if node_output.get("citations"):
                    citations = node_output["citations"]

                if node_output.get("final_answer"):
                    final_answer_parts = node_output["final_answer"]

    except Exception as e:
        logger.error(f"[runner_graph] streaming failed | session_id={session_id} | {e}")
        answer = "we ran into an issue processing your request. Please try again."
        redis_store.append_turn(session_id, "assistant", answer)
        redis_store.append_trace(session_id, latest_trace_log)
        yield {"type": "error", "message": answer}
        return

    if exit_stage:
        logger.info(f"[runner_graph] session_id={session_id} exited at {exit_stage}")
        redis_store.append_turn(session_id, "assistant", exit_message)
        redis_store.append_trace(session_id, latest_trace_log)
        yield {"type": "done", "exit_stage": exit_stage, "citations": {}}
        return

    final_answer = "".join(final_answer_parts) or "I couldn't generate an answer."
    redis_store.append_turn(session_id, "assistant", final_answer)
    redis_store.append_trace(session_id, latest_trace_log)
    yield {"type": "done", "exit_stage": None, "citations": citations}