import pytest

from Rag_backend.pipeline.ingestion import chunker


@pytest.fixture
def sample_elements():
    return [
        {
            "text": "First chunk",
            "page_number": 1,
            "bbox": [0, 0, 10, 10],
        }
    ]


def test_chunk_elements_success(monkeypatch, sample_elements):

    monkeypatch.setattr(
        chunker,
        "resolve_strategy",
        lambda chosen, session_id: "recursive_token",
    )

    expected_chunks = [
        {
            "chunk_id": "1",
            "text": "chunk",
        }
    ]

    monkeypatch.setattr(
        chunker,
        "chunk_document",
        lambda elements, strategy_name: expected_chunks,
    )

    chunks, strategy_name = chunker.chunk_elements(
        sample_elements,
        "recursive_token",
        "session1",
    )

    assert strategy_name == "recursive_token"
    assert chunks == expected_chunks


def test_chunk_elements_without_session(monkeypatch, sample_elements):

    monkeypatch.setattr(
        chunker,
        "resolve_strategy",
        lambda chosen, session_id: "fixed_size",
    )

    monkeypatch.setattr(
        chunker,
        "chunk_document",
        lambda elements, strategy_name: [],
    )

    chunks, strategy_name = chunker.chunk_elements(
        sample_elements,
        "fixed_size",
        None,
    )

    assert strategy_name == "fixed_size"
    assert chunks == []


def test_chunk_elements_resolve_strategy_failure(monkeypatch, sample_elements):

    def fake_resolve(chosen, session_id):
        raise ValueError("invalid strategy")

    monkeypatch.setattr(
        chunker,
        "resolve_strategy",
        fake_resolve,
    )

    with pytest.raises(ValueError, match="invalid strategy"):

        chunker.chunk_elements(
            sample_elements,
            "bad_strategy",
            "session1",
        )


def test_chunk_elements_chunk_document_failure(monkeypatch, sample_elements):

    monkeypatch.setattr(
        chunker,
        "resolve_strategy",
        lambda chosen, session_id: "semantic",
    )

    def fake_chunk(elements, strategy_name):
        raise RuntimeError("chunking failed")

    monkeypatch.setattr(
        chunker,
        "chunk_document",
        fake_chunk,
    )

    with pytest.raises(RuntimeError, match="chunking failed"):

        chunker.chunk_elements(
            sample_elements,
            "semantic",
            "session1",
        )


def test_chunk_elements_passes_correct_arguments(monkeypatch, sample_elements):

    calls = {}

    def fake_resolve(chosen, session_id):
        calls["chosen"] = chosen
        calls["session_id"] = session_id
        return "fixed_size"

    def fake_chunk(elements, strategy_name):
        calls["elements"] = elements
        calls["strategy"] = strategy_name
        return ["chunk"]

    monkeypatch.setattr(
        chunker,
        "resolve_strategy",
        fake_resolve,
    )

    monkeypatch.setattr(
        chunker,
        "chunk_document",
        fake_chunk,
    )

    chunker.chunk_elements(
        sample_elements,
        "fixed_size",
        "abc123",
    )

    assert calls["chosen"] == "fixed_size"
    assert calls["session_id"] == "abc123"
    assert calls["elements"] == sample_elements
    assert calls["strategy"] == "fixed_size"