from Rag_backend.graph.state import State


def exited(state: State) -> bool:
    """Every node that terminates the graph sets exit_stage itself —
    checking this one field covers each node's own exception/guardrail
    exit uniformly, instead of re-deriving pass/fail per node here."""
    return bool(state.get("exit_stage"))


def after_safety_check(state: State) -> str:
    if exited(state):
        return "trace_writer"
    return "topic_boundary_check"


def after_topic_boundary_check(state: State) -> str:
    if exited(state):
        return "trace_writer"
    return "query_encode"


def after_query_encode(state: State) -> str:
    if exited(state):
        return "trace_writer"
    return "retriever"


def after_retriever(state: State) -> str:
    if exited(state):
        return "trace_writer"
    return "fuse"


def after_sufficiency_gate(state: State) -> str:
    if exited(state):
        return "trace_writer"
    return "generation"


def after_hallucination(state: State) -> str:
    if state.get("hallucination_passed"):
        return "PII"
    if exited(state):
        return "trace_writer"
    return "generation"


def after_PII(state: State) -> str:
    if exited(state):
        return "trace_writer"
    return "answer_relevance_check"


def after_answer_relevance_check(state: State) -> str:
    if state.get("relevance_passed"):
        return "trace_writer"
    if exited(state):
        return "trace_writer"
    return "rewrite_query"