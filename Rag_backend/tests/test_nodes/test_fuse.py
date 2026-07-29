import pytest

from Rag_backend.nodes import fuse as fuse_node


@pytest.fixture
def base_state():
    return {
        "main_corpus_results": [
            {
                "chunk_id": "A",
                "source_collection": "main",
                "payload": {"chunk_text": "A"},
            },
            {
                "chunk_id": "B",
                "source_collection": "main",
                "payload": {"chunk_text": "B"},
            },
        ],
        "session_results": [
            {
                "chunk_id": "C",
                "source_collection": "session",
                "payload": {"chunk_text": "C"},
            }
        ],
        "trace_log": [],
    }


def test_rrf_scores(monkeypatch):

    monkeypatch.setattr(
        fuse_node.settings,
        "RRF_K",
        60,
    )

    scores = fuse_node.rrf_scores(
        [
            {"chunk_id": "a"},
            {"chunk_id": "b"},
            {"chunk_id": "c"},
        ]
    )

    assert scores["a"] == pytest.approx(1 / 61)

    assert scores["b"] == pytest.approx(1 / 62)

    assert scores["c"] == pytest.approx(1 / 63)


def test_fuse_success(monkeypatch, base_state):

    monkeypatch.setattr(
        fuse_node.settings,
        "RRF_K",
        60,
    )

    monkeypatch.setattr(
        fuse_node.settings,
        "FUSE_TOP_K",
        10,
    )

    result = fuse_node.fuse(base_state)

    fused = result["fused_results"]

    assert len(fused) == 3

    assert result["trace_log"][-1]["event"] == "success"


def test_duplicate_chunk_scores(monkeypatch):

    monkeypatch.setattr(
        fuse_node.settings,
        "RRF_K",
        60,
    )

    monkeypatch.setattr(
        fuse_node.settings,
        "FUSE_TOP_K",
        10,
    )

    state = {
        "main_corpus_results": [
            {
                "chunk_id": "A",
                "source_collection": "main",
                "payload": {},
            }
        ],
        "session_results": [
            {
                "chunk_id": "A",
                "source_collection": "session",
                "payload": {},
            }
        ],
        "trace_log": [],
    }

    result = fuse_node.fuse(state)

    assert len(result["fused_results"]) == 1

    expected = (1 / 61) + (1 / 61)

    assert result["fused_results"][0]["rrf_score"] == pytest.approx(expected)


def test_empty_results(monkeypatch):

    monkeypatch.setattr(
        fuse_node.settings,
        "FUSE_TOP_K",
        5,
    )

    state = {
        "main_corpus_results": [],
        "session_results": [],
        "trace_log": [],
    }

    result = fuse_node.fuse(state)

    assert result["fused_results"] == []

    assert result["trace_log"][-1]["event"] == "success"


def test_fuse_exception(monkeypatch):

    monkeypatch.setattr(
        fuse_node,
        "rrf_scores",
        lambda results: (_ for _ in ()).throw(
            RuntimeError("boom")
        ),
    )

    monkeypatch.setattr(
        fuse_node.settings,
        "FUSE_TOP_K",
        5,
    )

    state = {
        "main_corpus_results": [
            {
                "chunk_id": "A",
                "source_collection": "main",
                "payload": {},
            }
        ],
        "session_results": [
            {
                "chunk_id": "B",
                "source_collection": "session",
                "payload": {},
            }
        ],
        "trace_log": [],
    }

    result = fuse_node.fuse(state)

    assert len(result["fused_results"]) == 2

    assert result["trace_log"][-1]["event"] == "failed_continued"


def test_build_trace_entry():

    from datetime import datetime, timezone

    started = datetime.now(timezone.utc)

    trace = fuse_node.build_trace_entry(
        node="fuse",
        event="success",
        started_at=started,
        details={"count": 3},
    )

    assert trace["node"] == "fuse"

    assert trace["event"] == "success"

    assert trace["detail"]["count"] == 3

    assert "started_at" in trace

    assert "completed_at" in trace

    assert "elapsed_ms" in trace