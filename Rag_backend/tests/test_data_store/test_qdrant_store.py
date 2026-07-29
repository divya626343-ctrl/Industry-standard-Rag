import pytest

from Rag_backend.data_stores import qdrant_store as qs


class FakePoint:

    def __init__(self, point_id, score, payload):
        self.id = point_id
        self.score = score
        self.payload = payload


class FakeResult:

    def __init__(self, points):
        self.points = points


class FakeClient:

    def __init__(self):
        self.collections = set()
        self.created = []
        self.deleted = []
        self.upserts = []
        self.query_called = False

    def collection_exists(self, name):
        return name in self.collections

    def create_collection(self, **kwargs):
        self.created.append(kwargs)
        self.collections.add(kwargs["collection_name"])

    def delete_collection(self, name):
        self.deleted.append(name)
        self.collections.discard(name)

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)

    def query_points(self, **kwargs):
        self.query_called = True
        return FakeResult(
            [
                FakePoint(
                    "chunk1",
                    0.95,
                    {"text": "hello"},
                ),
                FakePoint(
                    "chunk2",
                    0.80,
                    {"text": "world"},
                ),
            ]
        )


@pytest.fixture
def store(monkeypatch):

    fake = FakeClient()

    qstore = qs.QdrantStore()

    monkeypatch.setattr(
        qstore,
        "client",
        fake,
    )

    return qstore, fake


def test_collection_exists(store):

    qstore, fake = store

    fake.collections.add("docs")

    assert qstore.collection_exists("docs")


def test_create_collection(store):

    qstore, fake = store

    qstore.create_collection(
        "docs",
        384,
    )

    assert fake.created

    assert fake.created[0]["collection_name"] == "docs"


def test_create_collection_existing(store):

    qstore, fake = store

    fake.collections.add("docs")

    qstore.create_collection(
        "docs",
        384,
    )

    assert len(fake.created) == 1


def test_delete_collection(store):

    qstore, fake = store

    fake.collections.add("docs")

    qstore.delete_collection("docs")

    assert fake.deleted == ["docs"]


def test_delete_collection_missing(store):

    qstore, fake = store

    qstore.delete_collection("missing")

    assert fake.deleted == []


def test_upsert_chunks(store):

    qstore, fake = store

    qstore.upsert_chunks(
        collection_name="docs",
        chunk_ids=["c1", "c2"],
        dense_vectors=[
            [0.1, 0.2],
            [0.3, 0.4],
        ],
        sparse_vectors=[
            {1: 0.5},
            {2: 0.7},
        ],
        payloads=[
            {"text": "one"},
            {"text": "two"},
        ],
    )

    assert len(fake.upserts) == 1

    assert fake.upserts[0]["collection_name"] == "docs"

    assert len(fake.upserts[0]["points"]) == 2


def test_search_hybrid_missing_collection(store):

    qstore, fake = store

    result = qstore.search_hybrid(
        "missing",
        [0.1],
        {1: 0.2},
    )

    assert result == []


def test_search_hybrid(store):

    qstore, fake = store

    fake.collections.add("docs")

    result = qstore.search_hybrid(
        "docs",
        [0.1],
        {1: 0.2},
    )

    assert fake.query_called

    assert len(result) == 2

    assert result[0]["chunk_id"] == "chunk1"

    assert result[0]["payload"]["text"] == "hello"


def test_search_dense_only_missing(store):

    qstore, fake = store

    result = qstore.search_dense_only(
        "missing",
        [0.1],
    )

    assert result == []


def test_search_dense_only(store):

    qstore, fake = store

    fake.collections.add("docs")

    result = qstore.search_dense_only(
        "docs",
        [0.1],
    )

    assert fake.query_called

    assert len(result) == 2

    assert result[1]["chunk_id"] == "chunk2"


def test_default_top_k(monkeypatch, store):

    qstore, fake = store

    fake.collections.add("docs")

    monkeypatch.setattr(
        qs.settings,
        "RETRIEVAL_TOP_K",
        7,
    )

    qstore.search_dense_only(
        "docs",
        [0.1],
    )

    assert fake.query_called