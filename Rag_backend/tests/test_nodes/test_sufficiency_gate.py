import pytest

from Rag_backend.nodes import sufficiency_gate as sg


@pytest.fixture
def base_state():
    return {
        "reranked_results": [],
        "fused_results": [],
        "trace_log": [],
    }


def test_sufficiency_gate_reranked_success(monkeypatch, base_state):

    monkeypatch.setattr(sg.settings, "SUFFICIENCY_SCORE", 0.5)

    base_state["reranked_results"] = [
        {"chunk_id": "c1", "rerank_score": 0.9},
        {"chunk_id": "c2", "rerank_score": 0.3},
        {"chunk_id": "c3", "rerank_score": 0.5},
    ]

    result = sg.sufficiency_gate(base_state)

    assert result["sufficient_results"] == [
        {"chunk_id": "c1", "rerank_score": 0.9},
        {"chunk_id": "c3", "rerank_score": 0.5},
    ]
    assert "exit_stage" not in result

    trace = result["trace_log"][0]
    assert trace["event"] == "success"
    assert trace["detail"]["source"] == "reranked"
    assert trace["detail"]["count"] == 2


def test_sufficiency_gate_fallback_to_fused_is_unfiltered(monkeypatch, base_state):

    monkeypatch.setattr(sg.settings, "SUFFICIENCY_SCORE", 0.5)

    base_state["reranked_results"] = []
    base_state["fused_results"] = [
        {"chunk_id": "c1", "fused_score": 0.9},
        {"chunk_id": "c2", "fused_score": 0.01},
    ]

    result = sg.sufficiency_gate(base_state)

    assert result["sufficient_results"] == base_state["fused_results"]
    assert "exit_stage" not in result

    trace = result["trace_log"][0]
    assert trace["event"] == "success"
    assert trace["detail"]["source"] == "fused_fallback"
    assert trace["detail"]["count"] == 2


def test_sufficiency_gate_reranked_all_below_threshold(monkeypatch, base_state):

    monkeypatch.setattr(sg.settings, "SUFFICIENCY_SCORE", 0.5)

    base_state["reranked_results"] = [
        {"chunk_id": "c1", "rerank_score": 0.2},
        {"chunk_id": "c2", "rerank_score": 0.1},
    ]

    result = sg.sufficiency_gate(base_state)

    assert result["sufficient_results"] == []
    assert result["exit_stage"] == "sufficiency_gate_no_match"
    assert (
        result["exit_message"]
        == "I don't have information about that in the documents I have access to."
    )

    trace = result["trace_log"][0]
    assert trace["event"] == "insufficient"
    assert trace["detail"]["source"] == "reranked"


def test_sufficiency_gate_both_empty(monkeypatch, base_state):

    monkeypatch.setattr(sg.settings, "SUFFICIENCY_SCORE", 0.5)

    result = sg.sufficiency_gate(base_state)

    assert result["sufficient_results"] == []
    assert result["exit_stage"] == "sufficiency_gate_no_match"

    trace = result["trace_log"][0]
    assert trace["event"] == "insufficient"
    assert trace["detail"]["source"] == "fused_fallback"


def test_sufficiency_gate_exception_on_missing_score_key(monkeypatch, base_state):

    monkeypatch.setattr(sg.settings, "SUFFICIENCY_SCORE", 0.5)

    base_state["reranked_results"] = [{"chunk_id": "c1"}]  # missing "rerank_score"

    result = sg.sufficiency_gate(base_state)

    assert result["sufficient_results"] is None
    assert result["exit_stage"] == "sufficiency_gate_error"
    assert (
        result["exit_message"]
        == "we ran into an issue processing your request. Please try again."
    )

    trace = result["trace_log"][0]
    assert trace["event"] == "failed"
    assert "rerank_score" in trace["detail"]["error"]


def test_build_trace_entry():

    from datetime import datetime, timezone

    started = datetime.now(timezone.utc)

    trace = sg.build_trace_entry(
        node="sufficiency_gate",
        event="success",
        started_at=started,
        details={"source": "reranked", "count": 2},
    )

    assert trace["node"] == "sufficiency_gate"
    assert trace["event"] == "success"
    assert "started_at" in trace
    assert "completed_at" in trace
    assert "elapsed_ms" in trace
    assert trace["detail"]["count"] == 2


def test_build_trace_entry_defaults_details_to_empty_dict():

    from datetime import datetime, timezone

    started = datetime.now(timezone.utc)

    trace = sg.build_trace_entry(
        node="sufficiency_gate",
        event="failed",
        started_at=started,
        details=None,
    )

    assert trace["detail"] == {}