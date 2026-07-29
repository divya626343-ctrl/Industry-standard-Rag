from typing import Literal
from pydantic import BaseModel
from Rag_backend.llm_client import call_llm_structured, TaskType
from Rag_backend.config.prompts import TOPIC_BOUNDARY_SYSTEM_PROMPT
from Rag_backend.config.settings import settings
from Rag_backend.data_stores.redis_store import redis_store


class TopicBoundaryResult(BaseModel):
    in_scope: bool
    category: Literal["shared_corpus_match", "session_doc_match", "out_of_scope"]
    reason: str


def build_scope_context(session_id: str | None) -> str:
    """Combines the static shared-corpus domain description with any
    session-uploaded doc summaries, since a query is in-scope if it
    matches either — multiple docs per session are supported, each
    keeping its own summary (see redis_store.get_doc_topic_summaries)."""
    scope_parts = [f"Shared corpus domain:\n{settings.CORPUS_DOMAIN_DESCRIPTION}"]

    if session_id:
        summaries = redis_store.get_doc_topic_summaries(session_id)
        if summaries:
            session_scope = "\n".join(f"- {s}" for s in summaries)
            scope_parts.append(f"Session-uploaded document topics:\n{session_scope}")

    return "\n\n".join(scope_parts)


def check_topic_boundary(rewritten_query: str, session_id: str | None) -> TopicBoundaryResult:
    scope_context = build_scope_context(session_id)

    return call_llm_structured(
        prompt=f"Scope:\n{scope_context}\n\nQuery to classify:\n{rewritten_query}",
        schema=TopicBoundaryResult,
        system=TOPIC_BOUNDARY_SYSTEM_PROMPT,
        task=TaskType.JUDGE,
        temperature=0.0,
    )