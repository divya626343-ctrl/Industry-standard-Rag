import base64

import pytest

from Rag_backend.workers import ingestion


def test_ingest_document_task_success(monkeypatch):

    expected_bytes = b"hello world"
    encoded = base64.b64encode(expected_bytes).decode()

    called = {}

    def fake_ingest_document(**kwargs):
        called.update(kwargs)
        return {
            "status": "success",
            "chunks": 5,
        }

    monkeypatch.setattr(
        ingestion,
        "ingest_document",
        fake_ingest_document,
    )

    result = ingestion.ingest_document_task.run(
        encoded,
        "pdf",
        "sample.pdf",
        "acme",
        "session123",
        "semantic",
    )

    assert result == {
        "status": "success",
        "chunks": 5,
    }

    assert called["file_bytes"] == expected_bytes
    assert called["file_format"] == "pdf"
    assert called["filename"] == "sample.pdf"
    assert called["org"] == "acme"
    assert called["session_id"] == "session123"
    assert called["chosen_strategy"] == "semantic"


def test_ingest_document_task_retry(monkeypatch):

    encoded = base64.b64encode(b"abc").decode()

    def fake_ingest_document(**kwargs):
        raise RuntimeError("index failed")

    monkeypatch.setattr(
        ingestion,
        "ingest_document",
        fake_ingest_document,
    )

    retry_called = {}

    def fake_retry(exc):
        retry_called["exc"] = exc
        raise RuntimeError("retry called")

    monkeypatch.setattr(
        ingestion.ingest_document_task,
        "retry",
        fake_retry,
    )

    with pytest.raises(RuntimeError, match="retry called"):

        ingestion.ingest_document_task.run(
            encoded,
            "pdf",
            "sample.pdf",
            "acme",
            "session123",
            "semantic",
        )

    assert isinstance(
        retry_called["exc"],
        RuntimeError,
    )

    assert str(retry_called["exc"]) == "index failed"


def test_invalid_base64_retry(monkeypatch):

    retry_called = {}

    def fake_retry(exc):
        retry_called["exc"] = exc
        raise RuntimeError("retry called")

    monkeypatch.setattr(
        ingestion.ingest_document_task,
        "retry",
        fake_retry,
    )

    with pytest.raises(RuntimeError, match="retry called"):

        ingestion.ingest_document_task.run(
            "not-valid-base64",
            "pdf",
            "sample.pdf",
        )

    assert retry_called["exc"] is not None