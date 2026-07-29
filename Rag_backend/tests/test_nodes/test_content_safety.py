import pytest

from Rag_backend.nodes import content_safety as cs


class FakeSafetyResult:
    def __init__(self, is_safe, category, reason):
        self.is_safe = is_safe
        self.category = category
        self.reason = reason


@pytest.fixture
def base_state():
    return {
        "rewritten_query": "What is AI?",
        "trace_log": [],
    }


def test_content_safety_pass(monkeypatch, base_state):

    monkeypatch.setattr(
        cs,
        "check_safety",
        lambda **kwargs: FakeSafetyResult(
            True,
            "safe",
            "Safe query",
        ),
    )

    result = cs.content_safety(base_state)

    assert result["safety"] is True

    assert len(result["trace_log"]) == 1

    trace = result["trace_log"][0]

    assert trace["event"] == "passed"
    assert trace["detail"]["is_safe"] is True
    assert trace["detail"]["category"] == "safe"


def test_content_safety_not_pass(monkeypatch, base_state):

    monkeypatch.setattr(
        cs,
        "check_safety",
        lambda **kwargs: FakeSafetyResult(
            False,
            "harmful_content_request",
            "Unsafe request",
        ),
    )

    result = cs.content_safety(base_state)

    assert result["safety"] is False

    assert result["exit_stage"] == "safety_check_error"

    assert result["exit_message"] == "I can't help with that request."

    trace = result["trace_log"][0]

    assert trace["event"] == "not passed"

    assert trace["detail"]["reason"] == "Unsafe request"

    assert trace["detail"]["category"] == "harmful_content_request"


def test_content_safety_exception(monkeypatch, base_state):

    def boom(**kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(
        cs,
        "check_safety",
        boom,
    )

    result = cs.content_safety(base_state)

    assert result["safety"] is False

    assert result["exit_stage"] == "safety_check_error"

    assert (
        result["exit_message"]
        == "we ran into an issue processing your request. Please try again."
    )

    trace = result["trace_log"][0]

    assert trace["event"] == "failed"

    assert trace["detail"]["error"] == "LLM unavailable"


def test_build_trace_entry():

    from datetime import datetime, timezone

    started = datetime.now(timezone.utc)

    trace = cs.build_trace_entry(
        node="content_safety",
        event="passed",
        started_at=started,
        details={"category": "safe"},
    )

    assert trace["node"] == "content_safety"

    assert trace["event"] == "passed"

    assert "started_at" in trace

    assert "completed_at" in trace

    assert "elapsed_ms" in trace

    assert trace["detail"]["category"] == "safe"