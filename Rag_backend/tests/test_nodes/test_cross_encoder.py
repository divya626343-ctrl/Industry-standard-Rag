import pytest

from Rag_backend.nodes import cross_encoder as ce


class FakeCrossEncoder:

    def __init__(self, scores):
        self.scores = scores
        self.calls = []

    def predict(self, pairs):
        self.calls.append(pairs)
        return self.scores


@pytest.fixture
def base_state():
    return {
        "rewritten_query": "What is AI?",
        "fused_results": [
            {
                "payload": {
                    "chunk_text": "Artificial Intelligence"
                }
            },
            {
                "payload": {
                    "chunk_text": "Machine Learning"
                }
            },
        ],
        "trace_log": [],
    }


def test_cross_encoder_success(monkeypatch, base_state):

    fake = FakeCrossEncoder([0.2, 0.9])

    monkeypatch.setattr(
        ce,
        "reranker_model",
        fake,
    )

    result = ce.cross_encoder(base_state)

    assert len(fake.calls) == 1

    assert fake.calls[0] == [
        (
            "What is AI?",
            "Artificial Intelligence",
        ),
        (
            "What is AI?",
            "Machine Learning",
        ),
    ]

    reranked = result["reranked_results"]

    assert len(reranked) == 2

    assert reranked[0]["rerank_score"] == 0.9
    assert reranked[1]["rerank_score"] == 0.2

    assert result["trace_log"][-1]["event"] == "success"


def test_cross_encoder_empty_candidates(monkeypatch):

    fake = FakeCrossEncoder([])

    monkeypatch.setattr(
        ce,
        "reranker_model",
        fake,
    )

    state = {
        "rewritten_query": "query",
        "fused_results": [],
        "trace_log": [],
    }

    result = ce.cross_encoder(state)

    assert result["reranked_results"] == []

    assert result["trace_log"][-1]["event"] == "success"


def test_cross_encoder_predict_exception(monkeypatch, base_state):

    class BrokenModel:

        def predict(self, pairs):
            raise RuntimeError("model failed")

    monkeypatch.setattr(
        ce,
        "reranker_model",
        BrokenModel(),
    )

    result = ce.cross_encoder(base_state)

    assert result["reranked_results"] == []

    assert result["trace_log"][-1]["event"] == "failed"

    assert result["trace_log"][-1]["detail"]["error"] == "model failed"


def test_build_trace_entry():

    from datetime import datetime, timezone

    started = datetime.now(timezone.utc)

    trace = ce.build_trace_entry(
        node="cross_encoder",
        event="success",
        started_at=started,
        details={"count": 2},
    )

    assert trace["node"] == "cross_encoder"

    assert trace["event"] == "success"

    assert trace["detail"]["count"] == 2

    assert "started_at" in trace

    assert "completed_at" in trace

    assert "elapsed_ms" in trace