from botocore.exceptions import ClientError

from Rag_backend.data_stores import object_store as os


class FakeBody:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data


class FakePaginator:
    def __init__(self, pages):
        self.pages = pages

    def paginate(self, **kwargs):
        return self.pages


class FakeClient:
    def __init__(self):
        self.head_calls = []
        self.put_calls = []
        self.get_calls = []
        self.delete_calls = []
        self.delete_objects_calls = []
        self.pages = []

    def head_object(self, **kwargs):
        self.head_calls.append(kwargs)

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)

    def get_object(self, **kwargs):
        self.get_calls.append(kwargs)
        return {"Body": FakeBody(b"pdf-bytes")}

    def delete_object(self, **kwargs):
        self.delete_calls.append(kwargs)

    def get_paginator(self, name):
        return FakePaginator(self.pages)

    def delete_objects(self, **kwargs):
        self.delete_objects_calls.append(kwargs)


def make_store():
    store = os.ObjectStore.__new__(os.ObjectStore)
    store.client = FakeClient()
    store.bucket = "bucket"
    return store


def test_build_key_shared():
    assert (
        os.build_key("doc1", org="acme")
        == "shared/acme/doc1/document.pdf"
    )


def test_build_key_shared_default_org():
    assert (
        os.build_key("doc1")
        == "shared/default/doc1/document.pdf"
    )


def test_build_key_session():
    assert (
        os.build_key("doc1", session_id="s1")
        == "session/s1/doc1/document.pdf"
    )


def test_file_exists_true():
    store = make_store()

    assert store.file_exists("k1") is True

    assert store.client.head_calls[0]["Key"] == "k1"


def test_file_exists_false_404():
    store = make_store()

    def raise_404(**kwargs):
        raise ClientError(
            {"Error": {"Code": "404"}},
            "HeadObject",
        )

    store.client.head_object = raise_404

    assert store.file_exists("k1") is False


def test_file_exists_false_nosuchkey():
    store = make_store()

    def raise_missing(**kwargs):
        raise ClientError(
            {"Error": {"Code": "NoSuchKey"}},
            "HeadObject",
        )

    store.client.head_object = raise_missing

    assert store.file_exists("k1") is False


def test_file_exists_other_error():
    store = make_store()

    def raise_other(**kwargs):
        raise ClientError(
            {"Error": {"Code": "403"}},
            "HeadObject",
        )

    store.client.head_object = raise_other

    try:
        store.file_exists("k1")
        assert False
    except ClientError:
        pass


def test_upload_file():
    store = make_store()

    key = store.upload_file(
        "k1",
        b"abc",
        "application/pdf",
    )

    assert key == "k1"

    call = store.client.put_calls[0]

    assert call["Bucket"] == "bucket"
    assert call["Key"] == "k1"
    assert call["Body"] == b"abc"
    assert call["ContentType"] == "application/pdf"


def test_get_file():
    store = make_store()

    data = store.get_file("k1")

    assert data == b"pdf-bytes"
    assert store.client.get_calls[0]["Key"] == "k1"


def test_delete_file_existing(monkeypatch):
    store = make_store()

    monkeypatch.setattr(
        store,
        "file_exists",
        lambda key: True,
    )

    store.delete_file("k1")

    assert len(store.client.delete_calls) == 1
    assert store.client.delete_calls[0]["Key"] == "k1"


def test_delete_file_missing(monkeypatch):
    store = make_store()

    monkeypatch.setattr(
        store,
        "file_exists",
        lambda key: False,
    )

    store.delete_file("k1")

    assert store.client.delete_calls == []


def test_delete_prefix_empty():
    store = make_store()

    store.client.pages = [{}]

    store.delete_prefix("session/s1/")

    assert store.client.delete_objects_calls == []


def test_delete_prefix_success():
    store = make_store()

    store.client.pages = [
        {
            "Contents": [
                {"Key": "a.pdf"},
                {"Key": "b.pdf"},
            ]
        }
    ]

    store.delete_prefix("session/s1/")

    assert len(store.client.delete_objects_calls) == 1

    delete_arg = store.client.delete_objects_calls[0]["Delete"]

    assert delete_arg["Objects"] == [
        {"Key": "a.pdf"},
        {"Key": "b.pdf"},
    ]


def test_delete_prefix_multiple_pages():
    store = make_store()

    store.client.pages = [
        {"Contents": [{"Key": "a.pdf"}]},
        {"Contents": [{"Key": "b.pdf"}]},
    ]

    store.delete_prefix("session/s1/")

    objs = store.client.delete_objects_calls[0]["Delete"]["Objects"]

    assert len(objs) == 2