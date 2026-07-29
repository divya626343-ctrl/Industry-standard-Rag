from datetime import datetime, timezone

import pytest

from Rag_backend.nodes import generation as gen


@pytest.fixture
def sample_chunks():
    return [
        {
            "chunk_id": "c1",
            "source_collection": "main",
            "payload": {
                "doc_id": "doc1",
                "page_number": 1,
                "chunk_text": "First chunk",
            },
        },
        {
            "chunk_id": "c2",
            "source_collection": "session",
            "payload": {
                "doc_id": "doc2",
                "page_number": 5,
                "chunk_text": "Second chunk",
            },
        },
    ]


@pytest.fixture
def base_state(sample_chunks):
    return {
        "rewritten_query": "What is AI?",
        "sufficient_results": sample_chunks,
        "trace_log": [],
    }


def test_build_citations(sample_chunks):

    citations = gen.build_citations(sample_chunks)

    assert len(citations) == 2

    assert citations[1]["chunk_id"] == "c1"
    assert citations[1]["doc_id"] == "doc1"
    assert citations[1]["page_number"] == 1
    assert citations[1]["source_collection"] == "main"

    assert citations[2]["chunk_id"] == "c2"


def test_call_with_local_retries_success(monkeypatch):

    monkeypatch.setattr(
        gen,
        "LOCAL_RETRY_ATTEMPTS",
        2,
    )

    monkeypatch.setattr(
        gen,
        "call_llm_structured",
        lambda **kwargs: "generated answer",
    )

    answer, error = gen.call_with_local_retries("prompt")

    assert answer == "generated answer"
    assert error is None


def test_call_with_local_retries_retry_then_success(monkeypatch):

    monkeypatch.setattr(
        gen,
        "LOCAL_RETRY_ATTEMPTS",
        3,
    )

    calls = {"count": 0}

    def fake_call(**kwargs):
        calls["count"] += 1

        if calls["count"] < 3:
            raise RuntimeError("temporary")

        return "success"

    monkeypatch.setattr(
        gen,
        "call_llm_structured",
        fake_call,
    )

    answer, error = gen.call_with_local_retries("prompt")

    assert answer == "success"
    assert error is None
    assert calls["count"] == 3


def test_call_with_local_retries_failure(monkeypatch):

    monkeypatch.setattr(
        gen,
        "LOCAL_RETRY_ATTEMPTS",
        2,
    )

    monkeypatch.setattr(
        gen,
        "call_llm_structured",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("boom")
        ),
    )

    answer, error = gen.call_with_local_retries("prompt")

    assert answer is None
    assert isinstance(error, RuntimeError)


def test_generation_success(monkeypatch, base_state):

    monkeypatch.setattr(
        gen,
        "build_generation_prompt",
        lambda query, chunks: "prompt",
    )

    monkeypatch.setattr(
        gen,
        "call_with_local_retries",
        lambda prompt: ("Generated answer", None),
    )

    result = gen.generation(base_state)

    assert result["draft_answer"] == "Generated answer"

    assert result["generation_fallback"] is False

    assert len(result["citations"]) == 2

    assert result["trace_log"][-1]["event"] == "success"


def test_generation_fallback(monkeypatch, base_state):

    monkeypatch.setattr(
        gen,
        "build_generation_prompt",
        lambda query, chunks: "prompt",
    )

    monkeypatch.setattr(
        gen,
        "call_with_local_retries",
        lambda prompt: (
            None,
            RuntimeError("LLM unavailable"),
        ),
    )

    result = gen.generation(base_state)

    assert result["generation_fallback"] is True

    assert "First chunk" in result["draft_answer"]
    assert "Second chunk" in result["draft_answer"]

    assert result["trace_log"][-1]["event"] == "failed"

    assert result["citations"][1]["chunk_id"] == "c1"


def test_generation_fallback_no_chunks(monkeypatch):

    monkeypatch.setattr(
        gen,
        "build_generation_prompt",
        lambda query, chunks: "prompt",
    )

    monkeypatch.setattr(
        gen,
        "call_with_local_retries",
        lambda prompt: (
            None,
            RuntimeError("failure"),
        ),
    )

    state = {
        "rewritten_query": "query",
        "sufficient_results": [],
        "trace_log": [],
    }

    result = gen.generation(state)

    assert result["generation_fallback"] is True

    assert "No relevant information was found" in result["draft_answer"]


def test_build_trace_entry():

    started = datetime.now(timezone.utc)

    trace = gen.build_trace_entry(
        node="generation",
        event="success",
        started_at=started,
        details={"count": 2},
    )

    assert trace["node"] == "generation"

    assert trace["event"] == "success"

    assert trace["detail"]["count"] == 2

    assert "started_at" in trace

    assert "completed_at" in trace

    assert "elapsed_ms" in trace