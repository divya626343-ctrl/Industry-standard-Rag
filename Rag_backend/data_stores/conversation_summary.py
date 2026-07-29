"""
conversation_memory.py
purpose : the only module that wires together the llm layer and the persistence layer for conversation history.
Neither of those two modules imports the other directly
"""

from Rag_backend.llm_client import call_llm_raw, TaskType

from Rag_backend.data_stores.redis_store import redis_store

def summarize_fold(existing_summary: str | None, new_messages: list[dict]) -> str:
    convo_text = "\n".join(f"{m['role']} : {m['content']}" for m in new_messages)

    prompt = (
        f"Existing summary of the conversation so far:\n"
        f"{existing_summary or '(no summary yet)'}\n\n"
        f"New messages to fold into the summary:\n{convo_text}\n\n"
        "Update the summary to concisely capture all important facts, decisions, "
        "and open questions from BOTH the existing summary and the new messages. "
        "Keep it factual, third-person, and compact — a few sentences, not a transcript."
    )

    return call_llm_raw(
        prompt=prompt,
        system="You are a conversation summarizer that preserves factual continuity for a RAG assistant.",
        task=TaskType.JUDGE,
        temperature=0.0,
    )


def get_conversation_context(session_id: str) -> tuple[str | None, list[dict]]:
    """
    Call BEFORE building the initial state for a new graph run.
    Returns (summary_or_None, recent_messages) — inject both into GraphState.
    Internally handles folding older messages into the summary if needed.
    """
    return redis_store.get_context_for_query(session_id, summarizer_fn=summarize_fold)

def record_turn(session_id: str, role: str, content: str) -> None:
    """
    Call AFTER a graph run completes, once for the user's message and once
    for the assistant's final answer. Also refreshes the session's last_active
    timestamp, since a processed message is what should reset the 30-minute
    inactivity clock (see session_sweep.py).
    """
    redis_store.append_turn(session_id, role, content)
    redis_store.heartbeat(session_id)


    