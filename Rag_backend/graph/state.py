
from typing import TypedDict, Literal, Any


class State(TypedDict):
    """
    State is maintained throughout the rag pipeline , help to maintain memroy in a conversation and provide required information 
    """
    session_id: str
    raw_query: str

    rewritten_query: str | None

    safety: bool | None

    topic_in_scope: bool | None

    exit_stage: Literal[None, "safety", "topic_boundary", "sufficiency", "guardrail_exhausted", "relevance"]

    exit_message: str | None

    dense_query_vector : list

    sparse_query_vector : dict[int, float]

    main_corpus_results: list[dict]

    session_results: list[dict]

    fused_results: list[dict]

    reranked_results : list[dict]

    sufficient_results: list[dict]

    generation_fallback : bool 

    draft_answer: str

    retry_counter: int

    hallucination_passed: bool | None

    final_answer: str | None

    citations: list[dict]

    pii_redaction_applied: bool

    relevance_passed: bool | None

    trace_log: list[dict]


def create_initial_state(session_id: str, query: str) -> State:
    return State(
        session_id=session_id,
        raw_query=query,
        rewritten_query="",
        safety=False,
        in_topic_scope=False,
        exit_stage=None,
        exit_message="",
        query_encode=[],
        main_corpus_results=[],
        session_results=[],
        fused_results=[],
        reranked_chunks=[],
        sufficient_chunks=[],
        generation_fallback=False,
        draft_answer="",
        retry_counter=0,
        hallucination_passed=False,
        final_answer="",
        citations=[],
        pii_redaction_applied=False,
        trace_log=[],
        relevance_passed=False,
    )