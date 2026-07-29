import pytest

from Rag_backend.pipeline.ingestion import embedder


class FakeDenseVector:

    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class FakeSparseVector:

    def __init__(self, indices, values):

        class FakeArray:

            def __init__(self, data):
                self.data = data

            def tolist(self):
                return self.data

        self.indices = FakeArray(indices)
        self.values = FakeArray(values)


class FakeDenseModel:

    def embed(self, texts):
        return [
            FakeDenseVector([0.1, 0.2]),
            FakeDenseVector([0.3, 0.4]),
        ]


class FakeSparseModel:

    def embed(self, texts):
        return [
            FakeSparseVector([1, 2], [0.5, 0.6]),
            FakeSparseVector([3], [0.7]),
        ]


@pytest.fixture
def sample_chunks():
    return [
        {"text": "First chunk"},
        {"text": "Second chunk"},
    ]


def test_embed_chunks_success(monkeypatch, sample_chunks):

    monkeypatch.setattr(
        embedder,
        "dense_model",
        FakeDenseModel(),
    )

    monkeypatch.setattr(
        embedder,
        "sparse_model",
        FakeSparseModel(),
    )

    result = embedder.embed_chunks(sample_chunks)

    assert len(result) == 2

    assert result[0]["dense"] == [0.1, 0.2]
    assert result[0]["sparse"] == {
        1: 0.5,
        2: 0.6,
    }

    assert result[1]["dense"] == [0.3, 0.4]
    assert result[1]["sparse"] == {
        3: 0.7,
    }


def test_embed_chunks_empty(monkeypatch):

    class EmptyDense:

        def embed(self, texts):
            return []

    class EmptySparse:

        def embed(self, texts):
            return []

    monkeypatch.setattr(
        embedder,
        "dense_model",
        EmptyDense(),
    )

    monkeypatch.setattr(
        embedder,
        "sparse_model",
        EmptySparse(),
    )

    result = embedder.embed_chunks([])

    assert result == []


def test_embed_chunks_dense_failure(monkeypatch, sample_chunks):

    class BrokenDense:

        def embed(self, texts):
            raise RuntimeError("dense embedding failed")

    monkeypatch.setattr(
        embedder,
        "dense_model",
        BrokenDense(),
    )

    monkeypatch.setattr(
        embedder,
        "sparse_model",
        FakeSparseModel(),
    )

    with pytest.raises(RuntimeError, match="dense embedding failed"):

        embedder.embed_chunks(sample_chunks)


def test_embed_chunks_sparse_failure(monkeypatch, sample_chunks):

    class BrokenSparse:

        def embed(self, texts):
            raise RuntimeError("sparse embedding failed")

    monkeypatch.setattr(
        embedder,
        "dense_model",
        FakeDenseModel(),
    )

    monkeypatch.setattr(
        embedder,
        "sparse_model",
        BrokenSparse(),
    )

    with pytest.raises(RuntimeError, match="sparse embedding failed"):

        embedder.embed_chunks(sample_chunks)


def test_embed_chunks_passes_texts(monkeypatch, sample_chunks):

    calls = {}

    class Dense:

        def embed(self, texts):
            calls["texts"] = texts
            return [
                FakeDenseVector([1]),
                FakeDenseVector([2]),
            ]

    class Sparse:

        def embed(self, texts):
            return [
                FakeSparseVector([0], [0.1]),
                FakeSparseVector([1], [0.2]),
            ]

    monkeypatch.setattr(
        embedder,
        "dense_model",
        Dense(),
    )

    monkeypatch.setattr(
        embedder,
        "sparse_model",
        Sparse(),
    )

    embedder.embed_chunks(sample_chunks)

    assert calls["texts"] == [
        "First chunk",
        "Second chunk",
    ]