import logging
from datetime import datetime, timezone

from Rag_backend.graph.state import State
from Rag_backend.config.settings import settings
from Rag_backend.llm_client import call_llm_raw, TaskType
from Rag_backend.config.prompts import GENERATION_SYSTEM_PROMPT, build_generation_prompt

logger = logging.getLogger(__name__)

LOCAL_RETRY_ATTEMPTS = getattr(settings, "GENERATION_LOCAL_RETRIES", 2)  


def build_citations(chunks: list[dict]) -> dict:
    """Citation map is derived purely from which chunks were used, not
    from the LLM's output — valid whether generation succeeds or falls back."""
    return {
        i + 1: {
            "chunk_id": c["chunk_id"],
            "doc_id": c["payload"]["doc_id"],
            "page_number": c["payload"]["page_number"],
            "source_collection": c["source_collection"],
        }
        for i, c in enumerate(chunks)
    }


def call_with_local_retries(prompt: str) -> tuple[str | None, Exception | None]:
    """Retries transient LLM errors (rate limits, timeouts) locally,
    BEFORE anything touches the shared hallucination/relevance retry
    counter"""


    last_error = None
    for attempt in range(1, LOCAL_RETRY_ATTEMPTS + 1):
        try:
            answer = call_llm_raw(
                prompt=prompt,
                system=GENERATION_SYSTEM_PROMPT,
                task=TaskType.GENERATION,
                temperature=0.0,
            )
            return answer, None
        except Exception as e:
            last_error = e
            logger.warning(f"[generation] local retry {attempt}/{LOCAL_RETRY_ATTEMPTS} failed | {e}")
    return None, last_error


def generation(state: State):
    """
    Generates a grounded, cited answer strictly from sufficient_results.
    Retries transient LLM errors locally (LOCAL_RETRY_ATTEMPTS) before

    Reads rewritten_query, sufficient_results
    writes generated_answer, citations, generation_fallback
    """
    node_name = "generation"
    started_at = datetime.now(timezone.utc)

    chunks = state.get('sufficient_results') or []
    citations = build_citations(chunks)
    logger.info(f"[{node_name}] started | chunk_count={len(chunks)}")

    prompt = build_generation_prompt(state['rewritten_query'], chunks)
    answer, error = call_with_local_retries(prompt)

    if answer is not None:
        logger.info(f"[{node_name}] success | answer_len={len(answer)}")

        trace_entry = build_trace_entry(
            node=node_name,
            event="success",
            started_at=started_at,
            details={"chunk_count": len(chunks), "answer_len": len(answer)},
        )

        return {
            **state,
            "draft_answer": answer,
            "citations": citations,
            "generation_fallback": False,
            "trace_log": state['trace_log'] + [trace_entry],
        }

    
    logger.error(f"[{node_name}] all local retries exhausted | falling back | {error}")

    fallback_answer = "I couldn't generate a full answer, but here are the relevant excerpts I found:\n\n" + (
        "\n\n".join(f"[{i+1}] {c['payload']['chunk_text']}" for i, c in enumerate(chunks))
        or "No relevant information was found to answer this query."
    )

    trace_entry = build_trace_entry(
        node=node_name,
        event="failed",
        started_at=started_at,
        details={"error": str(error), "chunk_count": len(chunks), "local_retries": LOCAL_RETRY_ATTEMPTS},
    )

    return {
        **state,
        "draft_answer": fallback_answer,
        "citations": citations,
        "generation_fallback": True,
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