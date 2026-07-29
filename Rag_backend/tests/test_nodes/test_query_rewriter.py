import pytest

from Rag_backend.nodes import query_rewriter as qr


class FakeQueryRewrite:
    def __init__(self, rewritten_query):
        self.rewritten_query = rewritten_query


@pytest.fixture
def base_state():
    return {
        "raw_query": "What about its pricing?",
        "session_id": "sess-123",
        "trace_log": [],
    }


def test_query_rewriter_success(monkeypatch, base_state):
    monkeypatch.setattr(
        qr, "QUERY_REWRTIE_SYSTEM_PROMPT", "Query: {query}\nContext: {context}"
    )

    monkeypatch.setattr(
        qr,
        "get_conversation_context",
        lambda session_id: (
            "User is asking about a SaaS analytics product.",
            [
                {"role": "user", "content": "Tell me about the product"},
                {"role": "assistant", "content": "It's a SaaS analytics tool."},
            ],
        ),
    )

    captured_kwargs = {}

    def fake_call_llm_structured(**kwargs):
        captured_kwargs.update(kwargs)
        return FakeQueryRewrite("What is the pricing of the SaaS analytics tool?")

    monkeypatch.setattr(qr, "call_llm_structured", fake_call_llm_structured)

    result = qr.rewrite_query(base_state)

    assert result["rewritten_query"] == "What is the pricing of the SaaS analytics tool?"
    assert len(result["trace_log"]) == 1

    trace = result["trace_log"][0]
    assert trace["node"] == "query_rewriter"
    assert trace["event"] == "success"
    assert trace["detail"]["rewritten_query"] == "What is the pricing of the SaaS analytics tool?"

    # current (flagged, not-yet-fixed) behavior: rewrite still uses GENERATION,
    # not the recommended cheaper JUDGE task type
    assert captured_kwargs["task"] == qr.TaskType.GENERATION
    assert captured_kwargs["schema"] is qr.QueryRewrite


def test_query_rewriter_llm_failure_falls_back_to_raw_query(monkeypatch, base_state):

    monkeypatch.setattr(
        qr, "QUERY_REWRTIE_SYSTEM_PROMPT", "Query: {query}\nContext: {context}"
    )

    recent_messages = [
        {"role": "user", "content": "Tell me about the product"},
        {"role": "assistant", "content": "It's a SaaS analytics tool."},
    ]

    monkeypatch.setattr(
        qr,
        "get_conversation_context",
        lambda session_id: ("some summary", recent_messages),
    )

    def boom(**kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(qr, "call_llm_structured", boom)

    result = qr.rewrite_query(base_state)

    expected = f"{base_state['raw_query']}\n {recent_messages}"
    assert result["rewritten_query"] == expected

    assert len(result["trace_log"]) == 1
    trace = result["trace_log"][0]
    assert trace["event"] == "failed"
    assert trace["detail"]["error"] == "LLM unavailable"

    # this node does not set exit_stage/exit_message on failure -- it degrades
    # to a best-effort fallback query instead of terminating the graph
    assert "exit_stage" not in result
    assert "exit_message" not in result


def test_query_rewriter_conversation_context_failure_raises_nameerror(monkeypatch, base_state):
    

    def boom(session_id):
        raise ConnectionError("redis unavailable")

    monkeypatch.setattr(qr, "get_conversation_context", boom)

    with pytest.raises(NameError):
        qr.rewrite_query(base_state)


def test_production_prompt_template_formats_successfully(monkeypatch, base_state):

    monkeypatch.setattr(
        qr,
        "get_conversation_context",
        lambda session_id: ("some summary", []),
    )

    captured_kwargs = {}

    def fake_call_llm_structured(**kwargs):
        captured_kwargs.update(kwargs)
        return FakeQueryRewrite("What is the pricing?")

    monkeypatch.setattr(qr, "call_llm_structured", fake_call_llm_structured)

    result = qr.rewrite_query(base_state)

    assert result["trace_log"][-1]["event"] == "success"
    assert result["rewritten_query"] == "What is the pricing?"
    assert base_state["raw_query"] in captured_kwargs["prompt"]
    assert "some summary" in captured_kwargs["prompt"]


def test_build_trace_entry():

    from datetime import datetime, timezone

    started = datetime.now(timezone.utc)

    trace = qr.build_trace_entry(
        node="query_rewriter",
        event="success",
        started_at=started,
        details={"rewritten_query": "What is the pricing?"},
    )

    assert trace["node"] == "query_rewriter"
    assert trace["event"] == "success"
    assert "started_at" in trace
    assert "completed_at" in trace
    assert "elapsed_ms" in trace
    assert trace["detail"]["rewritten_query"] == "What is the pricing?"