import pytest

from Rag_backend.nodes import topic_boundary_check as tbc


class FakeTopicBoundaryResult:
    def __init__(self, in_scope, category, reason):
        self.in_scope = in_scope
        self.category = category
        self.reason = reason


@pytest.fixture
def base_state():
    return {
        "rewritten_query": "What is the data retention policy for EU clients?",
        "session_id": "sess-123",
        "trace_log": [],
    }


def test_topic_boundary_check_pass(monkeypatch, base_state):

    monkeypatch.setattr(
        tbc,
        "check_topic_boundary",
        lambda **kwargs: FakeTopicBoundaryResult(
            True,
            "shared_corpus_match",
            "Matches shared corpus domain",
        ),
    )

    result = tbc.topic_boundary_check(base_state)

    assert result["topic_in_scope"] is True
    assert "exit_stage" not in result

    assert len(result["trace_log"]) == 1
    trace = result["trace_log"][0]
    assert trace["event"] == "passed"
    assert trace["detail"]["in_scope"] is True
    assert trace["detail"]["category"] == "shared_corpus_match"


def test_topic_boundary_check_not_passed(monkeypatch, base_state):

    monkeypatch.setattr(
        tbc,
        "check_topic_boundary",
        lambda **kwargs: FakeTopicBoundaryResult(
            False,
            "out_of_scope",
            "Query does not match any known document topic",
        ),
    )

    result = tbc.topic_boundary_check(base_state)

    assert result["topic_in_scope"] is False
    assert result["exit_stage"] == "topic_boundary"
    assert (
        result["exit_message"]
        == "I don't have information about that in the documents I have access to."
    )

    trace = result["trace_log"][0]
    assert trace["event"] == "not passed"
    assert trace["detail"]["reason"] == "Query does not match any known document topic"
    assert trace["detail"]["category"] == "out_of_scope"
    assert trace["detail"]["in_scope"] is False


def test_topic_boundary_check_exception(monkeypatch, base_state):

    def boom(**kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(tbc, "check_topic_boundary", boom)

    result = tbc.topic_boundary_check(base_state)

    assert result["topic_in_scope"] is False
    assert result["exit_stage"] == "topic_boundary_error"
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

    trace = tbc.build_trace_entry(
        node="topic_boundary_check",
        event="passed",
        started_at=started,
        details={"in_scope": True, "category": "shared_corpus_match"},
    )

    assert trace["node"] == "topic_boundary_check"
    assert trace["event"] == "passed"
    assert "started_at" in trace
    assert "completed_at" in trace
    assert "elapsed_ms" in trace
    assert trace["detail"]["category"] == "shared_corpus_match"


def test_build_trace_entry_defaults_details_to_empty_dict():

    from datetime import datetime, timezone

    started = datetime.now(timezone.utc)

    trace = tbc.build_trace_entry(
        node="topic_boundary_check",
        event="failed",
        started_at=started,
        details=None,
    )

    assert trace["detail"] == {}