import pytest

from Rag_backend.nodes import retriever as rt


class FakeVectorStore:
    def __init__(self, hits_by_collection):
        self.hits_by_collection = hits_by_collection
        self.calls = []

    def search_hybrid(self, collection_name, dense_query_vector, sparse_query_vector):
        self.calls.append(
            {
                "collection_name": collection_name,
                "dense_query_vector": dense_query_vector,
                "sparse_query_vector": sparse_query_vector,
            }
        )
        return [dict(hit) for hit in self.hits_by_collection.get(collection_name, [])]


def fake_collection_name(session_id=None):
    if session_id is None:
        return "shared_collection"
    return f"session_{session_id}_collection"


@pytest.fixture
def base_state():
    return {
        "dense_query_vector": [0.1, 0.2, 0.3],
        "sparse_query_vector": {0: 0.5, 5: 0.3},
        "session_id": "sess-123",
        "trace_log": [],
    }


def test_retriever_success_with_session(monkeypatch, base_state):

    fake_store = FakeVectorStore(
        {
            "shared_collection": [{"chunk_id": "c1", "score": 0.9}],
            "session_sess-123_collection": [{"chunk_id": "c2", "score": 0.8}],
        }
    )

    monkeypatch.setattr(rt, "vector_store", fake_store)
    monkeypatch.setattr(rt, "collection_name", fake_collection_name)

    result = rt.retriever(base_state)

    assert result["main_corpus_results"] == [
        {"chunk_id": "c1", "score": 0.9, "source_collection": "shared"}
    ]
    assert result["session_results"] == [
        {"chunk_id": "c2", "score": 0.8, "source_collection": "session"}
    ]

    assert len(fake_store.calls) == 2
    assert fake_store.calls[0]["collection_name"] == "shared_collection"
    assert fake_store.calls[1]["collection_name"] == "session_sess-123_collection"
    assert fake_store.calls[0]["dense_query_vector"] == base_state["dense_query_vector"]
    assert fake_store.calls[0]["sparse_query_vector"] == base_state["sparse_query_vector"]

    assert len(result["trace_log"]) == 1
    trace = result["trace_log"][0]
    assert trace["node"] == "retrieve"
    assert trace["event"] == "success"
    assert trace["detail"]["shared_hits"] == 1
    assert trace["detail"]["session_hits"] == 1


def test_retriever_success_without_session(monkeypatch, base_state):

    base_state["session_id"] = None

    fake_store = FakeVectorStore(
        {"shared_collection": [{"chunk_id": "c1", "score": 0.9}]}
    )

    monkeypatch.setattr(rt, "vector_store", fake_store)
    monkeypatch.setattr(rt, "collection_name", fake_collection_name)

    result = rt.retriever(base_state)

    assert result["main_corpus_results"] == [
        {"chunk_id": "c1", "score": 0.9, "source_collection": "shared"}
    ]
    assert result["session_results"] == []

    assert len(fake_store.calls) == 1
    assert fake_store.calls[0]["collection_name"] == "shared_collection"

    trace = result["trace_log"][0]
    assert trace["detail"]["shared_hits"] == 1
    assert trace["detail"]["session_hits"] == 0


def test_retriever_exception(monkeypatch, base_state):

    class BoomVectorStore:
        def search_hybrid(self, **kwargs):
            raise ConnectionError("qdrant unavailable")

    monkeypatch.setattr(rt, "vector_store", BoomVectorStore())
    monkeypatch.setattr(rt, "collection_name", fake_collection_name)

    result = rt.retriever(base_state)

    assert result["main_corpus_results"] is None
    assert result["session_results"] is None
    assert result["exit_stage"] == "retrieve_error"
    assert (
        result["exit_message"]
        == "we ran into an issue processing your request. Please try again."
    )

    trace = result["trace_log"][0]
    assert trace["event"] == "failed"
    assert trace["detail"]["error"] == "qdrant unavailable"


def test_retriever_missing_query_vectors(monkeypatch, base_state):

    del base_state["dense_query_vector"]

    monkeypatch.setattr(rt, "vector_store", FakeVectorStore({}))
    monkeypatch.setattr(rt, "collection_name", fake_collection_name)

    result = rt.retriever(base_state)

    assert result["exit_stage"] == "retrieve_error"
    assert "dense_query_vector" in result["trace_log"][0]["detail"]["error"]


def test_build_trace_entry():

    from datetime import datetime, timezone

    started = datetime.now(timezone.utc)

    trace = rt.build_trace_entry(
        node="retrieve",
        event="success",
        started_at=started,
        details={"shared_hits": 3, "session_hits": 1},
    )

    assert trace["node"] == "retrieve"
    assert trace["event"] == "success"
    assert "started_at" in trace
    assert "completed_at" in trace
    assert "elapsed_ms" in trace
    assert trace["detail"]["shared_hits"] == 3


def test_build_trace_entry_defaults_details_to_empty_dict():

    from datetime import datetime, timezone

    started = datetime.now(timezone.utc)

    trace = rt.build_trace_entry(
        node="retrieve",
        event="failed",
        started_at=started,
        details=None,
    )

    assert trace["detail"] == {}