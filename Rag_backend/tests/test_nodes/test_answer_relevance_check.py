import pytest

from Rag_backend.nodes import answer_relevance_check as arc


class FakeResult:
    def __init__(self, score, reason="reason"):
        self.relevance_score = score
        self.reason = reason


@pytest.fixture
def base_state():
    return {
        "generation_fallback": False,
        "rewritten_query": "What is AI?",
        "final_answer": "Artificial Intelligence",
        "retry_count": 0,
        "trace_log": [],
    }


def test_fallback_answer(monkeypatch, base_state):

    base_state["generation_fallback"] = True

    result = arc.answer_relevance_check(base_state)

    assert result["relevance_passed"] is True
    assert len(result["trace_log"]) == 1
    assert result["trace_log"][0]["event"] == "skipped_fallback"


def test_relevance_pass(monkeypatch, base_state):

    monkeypatch.setattr(
        arc,
        "check_answer_relevance",
        lambda q, a: FakeResult(0.95),
    )

    monkeypatch.setattr(
        arc.settings,
        "ANSWER_RELEVANCE_THRESHOLD",
        0.8,
    )

    result = arc.answer_relevance_check(base_state)

    assert result["relevance_passed"] is True
    assert result["retry_count"] == 0
    assert result["trace_log"][-1]["event"] == "passed"


def test_relevance_fail_retry(monkeypatch, base_state):

    monkeypatch.setattr(
        arc,
        "check_answer_relevance",
        lambda q, a: FakeResult(0.2, "irrelevant"),
    )

    monkeypatch.setattr(
        arc.settings,
        "ANSWER_RELEVANCE_THRESHOLD",
        0.8,
    )

    monkeypatch.setattr(
        arc.settings,
        "MAX_GUARDRAIL_RETRIES",
        2,
    )

    result = arc.answer_relevance_check(base_state)

    assert result["relevance_passed"] is False
    assert result["retry_count"] == 1
    assert result["trace_log"][-1]["event"] == "failed"

    detail = result["trace_log"][-1]["detail"]

    assert detail["score"] == 0.2
    assert detail["reason"] == "irrelevant"


def test_retry_cap_exceeded(monkeypatch, base_state):

    base_state["retry_count"] = 2

    monkeypatch.setattr(
        arc,
        "check_answer_relevance",
        lambda q, a: FakeResult(0.1),
    )

    monkeypatch.setattr(
        arc.settings,
        "ANSWER_RELEVANCE_THRESHOLD",
        0.8,
    )

    monkeypatch.setattr(
        arc.settings,
        "MAX_GUARDRAIL_RETRIES",
        2,
    )

    result = arc.answer_relevance_check(base_state)

    assert result["relevance_passed"] is False
    assert result["retry_count"] == 3
    assert result["exit_stage"] == "relevance_retry_cap_exceeded"
    assert "confident answer" in result["exit_message"]


def test_guardrail_exception(monkeypatch, base_state):

    def boom(*args):
        raise RuntimeError("LLM failed")

    monkeypatch.setattr(
        arc,
        "check_answer_relevance",
        boom,
    )

    result = arc.answer_relevance_check(base_state)

    assert result["relevance_passed"] is None
    assert result["exit_stage"] == "answer_relevance_check_error"
    assert result["trace_log"][-1]["event"] == "error"


def test_build_trace_entry():

    from datetime import datetime, timezone

    started = datetime.now(timezone.utc)

    trace = arc.build_trace_entry(
        node="node1",
        event="passed",
        started_at=started,
        details={"score": 0.95},
    )

    assert trace["node"] == "node1"
    assert trace["event"] == "passed"
    assert "started_at" in trace
    assert "completed_at" in trace
    assert "elapsed_ms" in trace
    assert trace["detail"]["score"] == 0.95