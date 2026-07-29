import pytest

from Rag_backend.pipeline import chunking_startegy as strategy


@pytest.fixture
def sample_elements():
    return [
        {
            "text": "First paragraph",
            "page_number": 1,
            "bbox": [0, 0, 10, 10],
        },
        {
            "text": "Second paragraph",
            "page_number": 2,
            "bbox": [10, 10, 20, 20],
        },
    ]


def test_tag_elements(sample_elements):

    result = strategy.tag_elements(sample_elements)

    assert "<<<EL0>>>First paragraph" in result
    assert "<<<EL1>>>Second paragraph" in result


def test_untag_chunk(sample_elements):

    chunk = "<<<EL0>>>First paragraph\n<<<EL1>>>Second paragraph"

    result = strategy.untag_chunk(
        chunk,
        sample_elements,
        0,
    )

    assert result["chunk_index"] == 0
    assert result["text"] == "First paragraph\nSecond paragraph"
    assert result["page_number"] == 1
    assert result["page_number_end"] == 2
    assert result["bbox"] == [0, 0, 10, 10]
    assert "chunk_id" in result


def test_untag_chunk_without_markers(sample_elements):

    result = strategy.untag_chunk(
        "plain text",
        sample_elements,
        2,
    )

    assert result["text"] == "plain text"
    assert result["page_number"] == 1
    assert result["page_number_end"] == 1


def test_split_and_map(monkeypatch, sample_elements):

    class FakeSplitter:

        def split_text(self, text):
            return [
                "<<<EL0>>>First paragraph",
                "<<<EL1>>>Second paragraph",
            ]

    chunks = strategy.split_and_map(
        sample_elements,
        FakeSplitter(),
    )

    assert len(chunks) == 2
    assert chunks[0]["page_number"] == 1
    assert chunks[1]["page_number"] == 2


def test_chunk_fixed_size(monkeypatch):

    class FakeSplitter:

        @classmethod
        def from_tiktoken_encoder(cls, **kwargs):
            return cls()

        def split_text(self, text):
            return ["<<<EL0>>>Chunk"]

    monkeypatch.setattr(
        strategy,
        "RecursiveCharacterTextSplitter",
        FakeSplitter,
    )

    elements = [
        {
            "text": "Chunk",
            "page_number": 1,
            "bbox": [0, 0, 1, 1],
        }
    ]

    chunks = strategy.chunk_fixed_size(elements)

    assert len(chunks) == 1
    assert chunks[0]["text"] == "Chunk"


def test_chunk_recursive_token(monkeypatch):

    class FakeSplitter:

        @classmethod
        def from_tiktoken_encoder(cls, **kwargs):
            return cls()

        def split_text(self, text):
            return ["<<<EL0>>>Chunk"]

    monkeypatch.setattr(
        strategy,
        "RecursiveCharacterTextSplitter",
        FakeSplitter,
    )

    elements = [
        {
            "text": "Chunk",
            "page_number": 1,
            "bbox": [0, 0, 1, 1],
        }
    ]

    chunks = strategy.chunk_recursive_token(elements)

    assert len(chunks) == 1


def test_chunk_semantic(monkeypatch):

    class FakeSemanticChunker:

        def __init__(self, embeddings):
            pass

        def split_text(self, text):
            return ["<<<EL0>>>Semantic"]

    class FakeEmbeddings:

        def __init__(self, model_name):
            pass

    monkeypatch.setattr(
        strategy,
        "SemanticChunker",
        FakeSemanticChunker,
    )

    monkeypatch.setattr(
        strategy,
        "HuggingFaceEmbeddings",
        FakeEmbeddings,
    )

    elements = [
        {
            "text": "Semantic",
            "page_number": 1,
            "bbox": [0, 0, 1, 1],
        }
    ]

    chunks = strategy.chunk_semantic(elements)

    assert len(chunks) == 1
    assert chunks[0]["text"] == "Semantic"


def test_resolve_strategy_locked(monkeypatch):

    monkeypatch.setattr(
        strategy.redis_store,
        "get_active_chunking_strategy",
        lambda session_id: "semantic",
    )

    result = strategy.resolve_strategy(
        "fixed_size",
        "session1",
    )

    assert result == "semantic"


def test_resolve_strategy_user_choice(monkeypatch):

    monkeypatch.setattr(
        strategy.redis_store,
        "get_active_chunking_strategy",
        lambda session_id: None,
    )

    result = strategy.resolve_strategy(
        "fixed_size",
        "session1",
    )

    assert result == "fixed_size"


def test_resolve_strategy_default(monkeypatch):

    monkeypatch.setattr(
        strategy.redis_store,
        "get_active_chunking_strategy",
        lambda session_id: None,
    )

    monkeypatch.setattr(
        strategy.settings,
        "CHUNKING_STRATEGY",
        "recursive_token",
    )

    result = strategy.resolve_strategy(
        None,
        None,
    )

    assert result == "recursive_token"


def test_resolve_strategy_invalid_default(monkeypatch):

    monkeypatch.setattr(
        strategy.redis_store,
        "get_active_chunking_strategy",
        lambda session_id: None,
    )

    monkeypatch.setattr(
        strategy.settings,
        "CHUNKING_STRATEGY",
        "invalid",
    )

    with pytest.raises(ValueError):

        strategy.resolve_strategy(
            None,
            None,
        )


def test_chunk_document(monkeypatch):

    monkeypatch.setitem(
        strategy.STRATEGIES,
        "fake",
        lambda elements: ["chunk1", "chunk2"],
    )

    result = strategy.chunk_document(
        [],
        "fake",
    )

    assert result == ["chunk1", "chunk2"]