import pytest

from Rag_backend.pipeline.ingestion import indexer


@pytest.fixture
def parsed_document():
    return {
        "doc_id": "doc123",
        "content_hash": "hash123",
        "source_file_uri": "shared/org/document.pdf",
        "elements": [
            {
                "text": "First chunk",
                "page_number": 1,
                "bbox": [0, 0, 10, 10],
            }
        ],
    }


@pytest.fixture
def chunk_output():
    return [
        {
            "chunk_id": "chunk1",
            "chunk_index": 0,
            "text": "First chunk",
            "page_number": 1,
            "bbox": [0, 0, 10, 10],
        }
    ]


@pytest.fixture
def embedding_output():
    return [
        {
            "dense": [0.1, 0.2],
            "sparse": {1: 0.5},
        }
    ]


def test_generate_doc_summary(monkeypatch):

    monkeypatch.setattr(
        indexer,
        "call_llm_raw",
        lambda **kwargs: "Summary",
    )

    elements = [{"text": "Hello"}, {"text": "World"}]

    assert indexer.generate_doc_summary(elements) == "Summary"


def test_ingest_document_success_shared(
    monkeypatch,
    parsed_document,
    chunk_output,
    embedding_output,
):

    monkeypatch.setattr(
        indexer,
        "parse_document",
        lambda *args, **kwargs: parsed_document,
    )

    monkeypatch.setattr(
        indexer,
        "chunk_elements",
        lambda *args, **kwargs: (chunk_output, "recursive_token"),
    )

    monkeypatch.setattr(
        indexer,
        "embed_chunks",
        lambda chunks: embedding_output,
    )

    monkeypatch.setattr(
        indexer,
        "collection_name",
        lambda session_id: "shared_collection",
    )

    monkeypatch.setattr(
        indexer.vector_store,
        "collection_exists",
        lambda collection: True,
    )

    monkeypatch.setattr(
        indexer.vector_store,
        "upsert_chunks",
        lambda **kwargs: None,
    )

    result = indexer.ingest_document(
        b"abc",
        "pdf",
        "sample.pdf",
    )

    assert result["chunks_indexed"] == 1
    assert result["strategy"] == "recursive_token"
    assert "doc_id" in result


def test_ingest_document_creates_collection(
    monkeypatch,
    parsed_document,
    chunk_output,
    embedding_output,
):

    created = {}

    monkeypatch.setattr(
        indexer,
        "parse_document",
        lambda *args, **kwargs: parsed_document,
    )

    monkeypatch.setattr(
        indexer,
        "chunk_elements",
        lambda *args, **kwargs: (chunk_output, "semantic"),
    )

    monkeypatch.setattr(
        indexer,
        "embed_chunks",
        lambda chunks: embedding_output,
    )

    monkeypatch.setattr(
        indexer,
        "collection_name",
        lambda session_id: "collection",
    )

    monkeypatch.setattr(
        indexer.vector_store,
        "collection_exists",
        lambda collection: False,
    )

    def fake_create(collection, dense_vector_size):
        created["collection"] = collection
        created["size"] = dense_vector_size

    monkeypatch.setattr(
        indexer.vector_store,
        "create_collection",
        fake_create,
    )

    monkeypatch.setattr(
        indexer.vector_store,
        "upsert_chunks",
        lambda **kwargs: None,
    )

    indexer.ingest_document(
        b"abc",
        "pdf",
        "sample.pdf",
    )

    assert created["collection"] == "collection"
    assert created["size"] == 384


def test_ingest_document_session_upload(
    monkeypatch,
    parsed_document,
    chunk_output,
    embedding_output,
):

    strategy_saved = {}
    summary_saved = {}

    monkeypatch.setattr(
        indexer,
        "parse_document",
        lambda *args, **kwargs: parsed_document,
    )

    monkeypatch.setattr(
        indexer,
        "chunk_elements",
        lambda *args, **kwargs: (chunk_output, "fixed_size"),
    )

    monkeypatch.setattr(
        indexer,
        "embed_chunks",
        lambda chunks: embedding_output,
    )

    monkeypatch.setattr(
        indexer,
        "collection_name",
        lambda session_id: "session_collection",
    )

    monkeypatch.setattr(
        indexer.vector_store,
        "collection_exists",
        lambda collection: True,
    )

    monkeypatch.setattr(
        indexer.vector_store,
        "upsert_chunks",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        indexer,
        "generate_doc_summary",
        lambda elements: "summary",
    )

    monkeypatch.setattr(
        indexer.redis_store,
        "set_active_chunking_strategy",
        lambda session, strategy: strategy_saved.update(
            {"session": session, "strategy": strategy}
        ),
    )

    monkeypatch.setattr(
        indexer.redis_store,
        "set_doc_topic_summary",
        lambda session, summary: summary_saved.update(
            {"session": session, "summary": summary}
        ),
    )

    result = indexer.ingest_document(
        b"abc",
        "pdf",
        "sample.pdf",
        session_id="session1",
    )

    assert result["strategy"] == "fixed_size"
    assert strategy_saved["strategy"] == "fixed_size"
    assert summary_saved["summary"] == "summary"


def test_ingest_document_parser_failure(monkeypatch):

    monkeypatch.setattr(
        indexer,
        "parse_document",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("parser failed")
        ),
    )

    with pytest.raises(RuntimeError, match="parser failed"):

        indexer.ingest_document(
            b"abc",
            "pdf",
            "sample.pdf",
        )


def test_ingest_document_chunker_failure(
    monkeypatch,
    parsed_document,
):

    monkeypatch.setattr(
        indexer,
        "parse_document",
        lambda *args, **kwargs: parsed_document,
    )

    monkeypatch.setattr(
        indexer,
        "chunk_elements",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("chunking failed")
        ),
    )

    with pytest.raises(RuntimeError, match="chunking failed"):

        indexer.ingest_document(
            b"abc",
            "pdf",
            "sample.pdf",
        )


def test_ingest_document_embedder_failure(
    monkeypatch,
    parsed_document,
    chunk_output,
):

    monkeypatch.setattr(
        indexer,
        "parse_document",
        lambda *args, **kwargs: parsed_document,
    )

    monkeypatch.setattr(
        indexer,
        "chunk_elements",
        lambda *args, **kwargs: (chunk_output, "recursive_token"),
    )

    monkeypatch.setattr(
        indexer,
        "embed_chunks",
        lambda chunks: (_ for _ in ()).throw(
            RuntimeError("embedding failed")
        ),
    )

    with pytest.raises(RuntimeError, match="embedding failed"):

        indexer.ingest_document(
            b"abc",
            "pdf",
            "sample.pdf",
        )


def test_ingest_document_upsert_failure(
    monkeypatch,
    parsed_document,
    chunk_output,
    embedding_output,
):

    monkeypatch.setattr(
        indexer,
        "parse_document",
        lambda *args, **kwargs: parsed_document,
    )

    monkeypatch.setattr(
        indexer,
        "chunk_elements",
        lambda *args, **kwargs: (chunk_output, "recursive_token"),
    )

    monkeypatch.setattr(
        indexer,
        "embed_chunks",
        lambda chunks: embedding_output,
    )

    monkeypatch.setattr(
        indexer,
        "collection_name",
        lambda session_id: "collection",
    )

    monkeypatch.setattr(
        indexer.vector_store,
        "collection_exists",
        lambda collection: True,
    )

    monkeypatch.setattr(
        indexer.vector_store,
        "upsert_chunks",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("qdrant failed")
        ),
    )

    with pytest.raises(RuntimeError, match="qdrant failed"):

        indexer.ingest_document(
            b"abc",
            "pdf",
            "sample.pdf",
        )


def test_ingest_document_payload_contents(
    monkeypatch,
    parsed_document,
    chunk_output,
    embedding_output,
):

    captured = {}

    monkeypatch.setattr(
        indexer,
        "parse_document",
        lambda *args, **kwargs: parsed_document,
    )

    monkeypatch.setattr(
        indexer,
        "chunk_elements",
        lambda *args, **kwargs: (chunk_output, "recursive_token"),
    )

    monkeypatch.setattr(
        indexer,
        "embed_chunks",
        lambda chunks: embedding_output,
    )

    monkeypatch.setattr(
        indexer,
        "collection_name",
        lambda session_id: "collection",
    )

    monkeypatch.setattr(
        indexer.vector_store,
        "collection_exists",
        lambda collection: True,
    )

    def fake_upsert(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        indexer.vector_store,
        "upsert_chunks",
        fake_upsert,
    )

    indexer.ingest_document(
        b"abc",
        "pdf",
        "sample.pdf",
    )

    payload = captured["payloads"][0]

    assert payload["doc_title"] == "sample.pdf"
    assert payload["file_format"] == "pdf"
    assert payload["content_hash"] == "hash123"
    assert payload["source_file_uri"] == "shared/org/document.pdf"

    assert captured["dense_vectors"] == [[0.1, 0.2]]
    assert captured["sparse_vectors"] == [{1: 0.5}]
    assert captured["chunk_ids"] == ["chunk1"]