from datetime import datetime, timezone

import pytest

from Rag_backend.nodes import hallucination_check as hc


class FakeResult:
    def __init__(self, faithful, category="supported", reason="reason"):
        self.is_faithful = faithful
        self.category = category
        self.reason = reason


@pytest.fixture
def base_state():
    return {
        "generation_fallback": False,
        "rewritten_query": "What is AI?",
        "draft_answer": "Artificial Intelligence",
        "sufficient_results": [],
        "retry_count": 0,
        "trace_log": [],
    }


def test_skip_generation_fallback(base_state):

    base_state["generation_fallback"] = True

    result = hc.hallucination_check(base_state)

    assert result["hallucination_passed"] is True

    assert result["trace_log"][-1]["event"] == "skipped_fallback"


def test_hallucination_pass(monkeypatch, base_state):

    monkeypatch.setattr(
        hc,
        "check_hallucination",
        lambda **kwargs: FakeResult(
            True,
            category="supported",
        ),
    )

    result = hc.hallucination_check(base_state)

    assert result["hallucination_passed"] is True

    assert result["retry_count"] == 0

    assert result["trace_log"][-1]["event"] == "passed"

    assert result["trace_log"][-1]["detail"]["category"] == "supported"


def test_hallucination_fail_retry(monkeypatch, base_state):

    monkeypatch.setattr(
        hc.settings,
        "MAX_GUARDRAIL_RETRIES",
        2,
    )

    monkeypatch.setattr(
        hc,
        "check_hallucination",
        lambda **kwargs: FakeResult(
            False,
            category="unsupported",
            reason="Not grounded",
        ),
    )

    result = hc.hallucination_check(base_state)

    assert result["hallucination_passed"] is False

    assert result["retry_count"] == 1

    assert result["trace_log"][-1]["event"] == "failed"

    assert result["trace_log"][-1]["detail"]["reason"] == "Not grounded"


def test_retry_cap_exceeded(monkeypatch, base_state):

    base_state["retry_count"] = 2

    monkeypatch.setattr(
        hc.settings,
        "MAX_GUARDRAIL_RETRIES",
        2,
    )

    monkeypatch.setattr(
        hc,
        "check_hallucination",
        lambda **kwargs: FakeResult(
            False,
            category="unsupported",
            reason="Bad answer",
        ),
    )

    result = hc.hallucination_check(base_state)

    assert result["hallucination_passed"] is False

    assert result["retry_count"] == 3

    assert result["exit_stage"] == "hallucination_retry_cap_exceeded"

    assert "confident" in result["exit_message"]


def test_guardrail_exception(monkeypatch, base_state):

    def boom(**kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(
        hc,
        "check_hallucination",
        boom,
    )

    result = hc.hallucination_check(base_state)

    assert result["hallucination_passed"] is None

    assert result["exit_stage"] == "hallucination_check_error"

    assert result["trace_log"][-1]["event"] == "error"

    assert result["trace_log"][-1]["detail"]["error"] == "LLM unavailable"


def test_build_trace_entry():

    started = datetime.now(timezone.utc)

    trace = hc.build_trace_entry(
        node="hallucination_check",
        event="passed",
        started_at=started,
        details={"category": "supported"},
    )

    assert trace["node"] == "hallucination_check"

    assert trace["event"] == "passed"

    assert trace["detail"]["category"] == "supported"

    assert "started_at" in trace

    assert "completed_at" in trace

    assert "elapsed_ms" in trace