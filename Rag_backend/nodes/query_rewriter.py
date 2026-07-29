import logging
from datetime import datetime, timezone
from Rag_backend.graph.state import State
from Rag_backend.config.settings import settings
from pydantic import BaseModel, Field
from Rag_backend.config.prompts import QUERY_REWRTIE_SYSTEM_PROMPT
from Rag_backend.data_stores.conversation_summary import get_conversation_context
from Rag_backend.llm_client import call_llm_structured, TaskType

logger = logging.getLogger(__name__)

class QueryRewrite(BaseModel):
    rewritten_query: str = Field(..., description = "expanded query with full conversation context")


def rewrite_query(state: State):
    """
    This is the first node in graph 
    takes the query , rewrite it 
    according to the context of the conversation

    on failure;
    status = "failed"
    original query is preserved
    trace entry records error
    """

    started_at = datetime.now(timezone.utc)
    node_name = "query_rewriter"

    logger.info(f"[{node_name}] starting | query='{state['raw_query']}'")
    
    try:

        summary, recent_messages = get_conversation_context(state['session_id'])
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in recent_messages)
        context_block = f"Summary: {summary or 'none'}\nRecent turns:\n{history_text}"

        prompt = QUERY_REWRTIE_SYSTEM_PROMPT.format(query = state['raw_query'], context = context_block)

        result: QueryRewrite = call_llm_structured(
            prompt = prompt,
            system= """You are a helpful assistant that rewrites a user's follow-up question into a clear, standalone question, using the conversation so far to resolve any pronouns or missing context. 
            Keep the user's original intent exactly — don't add new information or change what they're asking.
             """,
            schema = QueryRewrite,
            task = TaskType.GENERATION
        )
        
        logger.info(f"[{node_name}] success |"
                    f"rewritten_query = '{result.rewritten_query}'")
        
        trace_entry = build_trace_entry(
            node = node_name,
            event = "success",
            started_at = started_at,
            details = {
                "rewritten_query" : result.rewritten_query
            }
        )
       
        return {
           **state,
           "rewritten_query" : result.rewritten_query,
           "trace_log": state["trace_log"] + [trace_entry],
       }
    
    except Exception as e:

        logger.error(f"[{node_name}] failed | error = '{e}'")

        trace_entry = build_trace_entry(
            node = node_name,
            event = "failed",
            started_at = started_at,
            details = {"error": str(e)}
        )

        logger.info(f"[{node_name}] falling back to original query with recent messages")

        combined = f"{state['raw_query']}\n {recent_messages}"

        return {
           **state,
           "rewritten_query" : combined,
           "trace_log": state["trace_log"] + [trace_entry],
       }
    
def build_trace_entry(
    node: str,
    event: str,                 # "success" | "failed"
    started_at: datetime,
    details: dict | None = None
) -> dict:
    completed_at = datetime.now(timezone.utc)
    return {
        "node": node,
        "event": event,
        "started_at":started_at.isoformat() ,
        "completed_at": completed_at.isoformat(),
        "elapsed_ms": int((completed_at - started_at).total_seconds() * 1000),
        "detail": details
    }