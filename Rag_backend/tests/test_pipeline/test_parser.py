import hashlib
import subprocess

import pytest

from Rag_backend.pipeline.ingestion import parser


def test_compute_content_hash_returns_sha256():

    data = b"hello world"

    expected = hashlib.sha256(data).hexdigest()

    assert parser.compute_content_hash(data) == expected


def test_compute_content_hash_same_input_same_hash():

    data = b"sample bytes"

    hash1 = parser.compute_content_hash(data)
    hash2 = parser.compute_content_hash(data)

    assert hash1 == hash2


def test_convert_to_pdf_pdf_passthrough():

    pdf_bytes = b"%PDF-1.4 sample pdf"

    result = parser.convert_to_pdf(pdf_bytes, "pdf")

    assert result == pdf_bytes


def test_convert_to_pdf_invalid_format():

    with pytest.raises(ValueError, match="unsupported file_format"):

        parser.convert_to_pdf(b"abc", "txt")


def test_convert_to_pdf_docx_success(monkeypatch, tmp_path):

    class FakeTemporaryDirectory:

        def __enter__(self):
            return str(tmp_path)

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_run(cmd, check, capture_output):
        output = tmp_path / "input.pdf"
        output.write_bytes(b"converted pdf")

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.tempfile.TemporaryDirectory",
        FakeTemporaryDirectory,
    )

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.subprocess.run",
        fake_run,
    )

    result = parser.convert_to_pdf(b"doc bytes", "docx")

    assert result == b"converted pdf"


def test_convert_to_pdf_html_success(monkeypatch, tmp_path):

    class FakeTemporaryDirectory:

        def __enter__(self):
            return str(tmp_path)

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_run(cmd, check, capture_output):
        (tmp_path / "input.pdf").write_bytes(b"html pdf")

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.tempfile.TemporaryDirectory",
        FakeTemporaryDirectory,
    )

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.subprocess.run",
        fake_run,
    )

    result = parser.convert_to_pdf(b"<h1>Hello</h1>", "html")

    assert result == b"html pdf"


def test_convert_to_pdf_missing_output(monkeypatch, tmp_path):

    class FakeTemporaryDirectory:

        def __enter__(self):
            return str(tmp_path)

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.tempfile.TemporaryDirectory",
        FakeTemporaryDirectory,
    )

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.subprocess.run",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(RuntimeError, match="conversion produced no output"):

        parser.convert_to_pdf(b"abc", "docx")


def test_convert_to_pdf_subprocess_failure(monkeypatch, tmp_path):

    class FakeTemporaryDirectory:

        def __enter__(self):
            return str(tmp_path)

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.tempfile.TemporaryDirectory",
        FakeTemporaryDirectory,
    )

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "libreoffice")

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.subprocess.run",
        fake_run,
    )

    with pytest.raises(subprocess.CalledProcessError):

        parser.convert_to_pdf(b"abc", "docx")


def test_extract_elements(monkeypatch):

    class FakePage:

        def get_text(self, mode):
            return [
                (0.1234, 1.2345, 10.9876, 20.5432, "First block", 0, 0),
                (5.5555, 6.6666, 7.7777, 8.8888, "Second block", 1, 0),
            ]

    class FakeDocument:

        def __enter__(self):
            return [FakePage()]

        def __exit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.fitz.open",
        lambda **kwargs: FakeDocument(),
    )

    result = parser.extract_elements(b"pdf")

    assert len(result) == 2

    assert result[0]["text"] == "First block"
    assert result[0]["page_number"] == 1
    assert result[0]["bbox"] == [0.12, 1.23, 10.99, 20.54]


def test_extract_elements_skips_empty_blocks(monkeypatch):

    class FakePage:

        def get_text(self, mode):
            return [
                (0, 0, 1, 1, "   ", 0, 0),
                (1, 1, 2, 2, "Valid", 1, 0),
            ]

    class FakeDocument:

        def __enter__(self):
            return [FakePage()]

        def __exit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.fitz.open",
        lambda **kwargs: FakeDocument(),
    )

    result = parser.extract_elements(b"pdf")

    assert len(result) == 1
    assert result[0]["text"] == "Valid"


def test_extract_elements_multiple_pages(monkeypatch):

    class FakePage:

        def __init__(self, text):
            self.text = text

        def get_text(self, mode):
            return [
                (0, 0, 1, 1, self.text, 0, 0),
            ]

    class FakeDocument:

        def __enter__(self):
            return [
                FakePage("Page 1"),
                FakePage("Page 2"),
            ]

        def __exit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.fitz.open",
        lambda **kwargs: FakeDocument(),
    )

    result = parser.extract_elements(b"pdf")

    assert result[0]["page_number"] == 1
    assert result[1]["page_number"] == 2


def test_parse_document_success(monkeypatch):

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.compute_content_hash",
        lambda _: "hash123",
    )

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.convert_to_pdf",
        lambda *_: b"pdf",
    )

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.build_key",
        lambda *args, **kwargs: "shared/org/doc/document.pdf",
    )

    uploaded = {}

    def fake_upload(key, data, content_type):
        uploaded["key"] = key
        uploaded["data"] = data
        uploaded["content_type"] = content_type

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.object_store.upload_file",
        fake_upload,
    )

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.extract_elements",
        lambda _: [{"text": "hello"}],
    )

    result = parser.parse_document(
        file_bytes=b"abc",
        file_format="pdf",
        doc_id="doc1",
        org="org1",
    )

    assert result["doc_id"] == "doc1"
    assert result["content_hash"] == "hash123"
    assert result["source_file_uri"] == "shared/org/doc/document.pdf"
    assert result["elements"] == [{"text": "hello"}]

    assert uploaded["content_type"] == parser.PDF_CONTENT_TYPE


def test_parse_document_upload_failure(monkeypatch):

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.compute_content_hash",
        lambda _: "hash",
    )

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.convert_to_pdf",
        lambda *_: b"pdf",
    )

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.build_key",
        lambda *args, **kwargs: "key",
    )

    def fake_upload(*args, **kwargs):
        raise RuntimeError("upload failed")

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.object_store.upload_file",
        fake_upload,
    )

    with pytest.raises(RuntimeError, match="upload failed"):

        parser.parse_document(
            b"abc",
            "pdf",
            "doc1",
        )


def test_parse_document_extract_failure(monkeypatch):

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.compute_content_hash",
        lambda _: "hash",
    )

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.convert_to_pdf",
        lambda *_: b"pdf",
    )

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.build_key",
        lambda *args, **kwargs: "key",
    )

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.object_store.upload_file",
        lambda *args, **kwargs: None,
    )

    def fake_extract(_):
        raise RuntimeError("extract failed")

    monkeypatch.setattr(
        "Rag_backend.pipeline.ingestion.parser.extract_elements",
        fake_extract,
    )

    with pytest.raises(RuntimeError, match="extract failed"):

        parser.parse_document(
            b"abc",
            "pdf",
            "doc1",
        )