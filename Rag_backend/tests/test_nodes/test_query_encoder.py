from datetime import datetime, timezone

import pytest

from Rag_backend.nodes import query_encoder as qe


class FakeDenseEmbedding:

    def __init__(self, values):
        self._values = values

    def tolist(self):
        return self._values


class FakeDenseModel:

    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(texts)
        yield FakeDenseEmbedding([0.1, 0.2, 0.3])


class FakeSparseEmbedding:

    def __init__(self):
        self.indices = FakeDenseEmbedding([1, 3, 5])
        self.values = FakeDenseEmbedding([0.4, 0.5, 0.6])


class FakeSparseModel:

    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(texts)
        yield FakeSparseEmbedding()


@pytest.fixture
def base_state():
    return {
        "rewritten_query": "What is AI?",
        "trace_log": [],
    }


def test_query_encode_success(monkeypatch, base_state):

    dense = FakeDenseModel()
    sparse = FakeSparseModel()

    monkeypatch.setattr(qe, "dense_model", dense)
    monkeypatch.setattr(qe, "sparse_model", sparse)

    result = qe.query_encode(base_state)

    assert dense.calls == [["What is AI?"]]
    assert sparse.calls == [["What is AI?"]]

    assert result["dense_query_vector"] == [0.1, 0.2, 0.3]

    assert result["sparse_query_vector"] == {
        1: 0.4,
        3: 0.5,
        5: 0.6,
    }

    assert result["trace_log"][-1]["event"] == "success"

    assert result["trace_log"][-1]["detail"]["dense_dim"] == 3

    assert result["trace_log"][-1]["detail"]["sparse_terms"] == 3


def test_query_encode_failure(monkeypatch, base_state):

    class BrokenDense:

        def embed(self, texts):
            raise RuntimeError("embedding failed")

    monkeypatch.setattr(qe, "dense_model", BrokenDense())

    result = qe.query_encode(base_state)

    assert result["dense_query_vector"] is None

    assert result["sparse_query_vector"] is None

    assert result["exit_stage"] == "query_encode_error"

    assert result["trace_log"][-1]["event"] == "failed"

    assert (
        result["trace_log"][-1]["detail"]["error"]
        == "embedding failed"
    )


def test_build_trace_entry():

    started = datetime.now(timezone.utc)

    trace = qe.build_trace_entry(
        node="query_encode",
        event="success",
        started_at=started,
        details={"dense_dim": 384},
    )

    assert trace["node"] == "query_encode"

    assert trace["event"] == "success"

    assert trace["detail"]["dense_dim"] == 384

    assert "started_at" in trace

    assert "completed_at" in trace

    assert "elapsed_ms" in trace