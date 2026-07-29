from Rag_backend.graph import router as rt


def test_exited_true_when_exit_stage_set():
    assert rt.exited({"exit_stage": "content_safety_error"}) is True


def test_exited_false_when_exit_stage_missing():
    assert rt.exited({}) is False


def test_exited_false_when_exit_stage_none():
    assert rt.exited({"exit_stage": None}) is False


def test_after_safety_check_routes_to_trace_writer_on_exit():
    assert rt.after_safety_check({"exit_stage": "safety_check_error"}) == "trace_writer"


def test_after_safety_check_routes_to_topic_boundary_check():
    assert rt.after_safety_check({}) == "topic_boundary_check"


def test_after_topic_boundary_check_routes_to_trace_writer_on_exit():
    assert rt.after_topic_boundary_check({"exit_stage": "topic_boundary"}) == "trace_writer"


def test_after_topic_boundary_check_routes_to_query_encode():
    assert rt.after_topic_boundary_check({}) == "query_encode"


def test_after_query_encode_routes_to_trace_writer_on_exit():
    assert rt.after_query_encode({"exit_stage": "query_encode_error"}) == "trace_writer"


def test_after_query_encode_routes_to_retriever():
    assert rt.after_query_encode({}) == "retriever"


def test_after_retriever_routes_to_trace_writer_on_exit():
    assert rt.after_retriever({"exit_stage": "retrieve_error"}) == "trace_writer"


def test_after_retriever_routes_to_fuse():
    assert rt.after_retriever({}) == "fuse"


def test_after_sufficiency_gate_routes_to_trace_writer_on_exit():
    assert rt.after_sufficiency_gate({"exit_stage": "sufficiency_gate_no_match"}) == "trace_writer"


def test_after_sufficiency_gate_routes_to_generation():
    assert rt.after_sufficiency_gate({}) == "generation"


def test_after_hallucination_routes_to_pii_when_passed():
    assert rt.after_hallucination({"hallucination_passed": True}) == "PII"


def test_after_hallucination_passed_takes_priority_over_exit_stage():
    state = {"hallucination_passed": True, "exit_stage": "hallucination_check_error"}
    assert rt.after_hallucination(state) == "PII"


def test_after_hallucination_routes_to_trace_writer_on_exit_when_not_passed():
    state = {"hallucination_passed": False, "exit_stage": "hallucination_check_error"}
    assert rt.after_hallucination(state) == "trace_writer"


def test_after_hallucination_routes_to_generation_for_retry():
    state = {"hallucination_passed": False}
    assert rt.after_hallucination(state) == "generation"


def test_after_hallucination_missing_flag_and_no_exit_routes_to_generation():
    assert rt.after_hallucination({}) == "generation"


def test_after_pii_routes_to_trace_writer_on_exit():
    assert rt.after_PII({"exit_stage": "pii_error"}) == "trace_writer"


def test_after_pii_routes_to_answer_relevance_check():
    assert rt.after_PII({}) == "answer_relevance_check"


def test_after_answer_relevance_check_routes_to_trace_writer_when_passed():
    assert rt.after_answer_relevance_check({"relevance_passed": True}) == "trace_writer"


def test_after_answer_relevance_check_routes_to_trace_writer_on_exit_when_not_passed():
    state = {"relevance_passed": False, "exit_stage": "answer_relevance_error"}
    assert rt.after_answer_relevance_check(state) == "trace_writer"


def test_after_answer_relevance_check_routes_to_rewrite_query_for_retry():
    state = {"relevance_passed": False}
    assert rt.after_answer_relevance_check(state) == "rewrite_query"


def test_after_answer_relevance_check_missing_flag_and_no_exit_routes_to_rewrite_query():
    assert rt.after_answer_relevance_check({}) == "rewrite_query"