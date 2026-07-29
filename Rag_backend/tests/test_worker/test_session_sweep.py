import pytest

from Rag_backend.workers import session_sweep as ss


class FakeVectorStore:

    def __init__(self):
        self.deleted = []

    def delete_collection(self, name):
        self.deleted.append(name)


class BrokenVectorStore:

    def delete_collection(self, name):
        raise RuntimeError("qdrant failed")


class FakeRedisStore:

    def __init__(self):
        self.cleaned = []
        self.expired = []

    def cleanup_session(self, session_id):
        self.cleaned.append(session_id)

    def get_expired_sessions(self):
        return self.expired


@pytest.fixture
def fake_redis():
    return FakeRedisStore()


def test_teardown_session_success(monkeypatch, fake_redis):

    vector = FakeVectorStore()

    monkeypatch.setattr(ss, "vector_store", vector)
    monkeypatch.setattr(ss, "redis_store", fake_redis)
    monkeypatch.setattr(ss, "collection_name", lambda sid: f"collection_{sid}")

    ss.teardown_session("abc")

    assert vector.deleted == ["collection_abc"]

    assert fake_redis.cleaned == ["abc"]


def test_teardown_session_qdrant_failure(monkeypatch, fake_redis):

    monkeypatch.setattr(
        ss,
        "vector_store",
        BrokenVectorStore(),
    )

    monkeypatch.setattr(ss, "redis_store", fake_redis)
    monkeypatch.setattr(ss, "collection_name", lambda sid: f"collection_{sid}")

    with pytest.raises(RuntimeError):
        ss.teardown_session("abc")

    # Redis cleanup should still happen.
    assert fake_redis.cleaned == ["abc"]


def test_end_session_now(monkeypatch):

    called = {}

    def fake_teardown(session_id):
        called["id"] = session_id

    monkeypatch.setattr(
        ss,
        "teardown_session",
        fake_teardown,
    )

    ss.end_session_now("xyz")

    assert called["id"] == "xyz"


def test_sweep_expired_sessions_success(monkeypatch, fake_redis):

    fake_redis.expired = ["a", "b", "c"]

    monkeypatch.setattr(
        ss,
        "redis_store",
        fake_redis,
    )

    called = []

    def fake_teardown(session_id):
        called.append(session_id)

    monkeypatch.setattr(
        ss,
        "teardown_session",
        fake_teardown,
    )

    result = ss.sweep_expired_sessions()

    assert called == ["a", "b", "c"]

    assert result == {
        "swept": 3,
        "failed": 0,
        "checked": 3,
    }


def test_sweep_expired_sessions_partial_failure(monkeypatch, fake_redis):

    fake_redis.expired = ["a", "b", "c"]

    monkeypatch.setattr(
        ss,
        "redis_store",
        fake_redis,
    )

    def fake_teardown(session_id):
        if session_id == "b":
            raise RuntimeError("failed")

    monkeypatch.setattr(
        ss,
        "teardown_session",
        fake_teardown,
    )

    result = ss.sweep_expired_sessions()

    assert result == {
        "swept": 2,
        "failed": 1,
        "checked": 3,
    }


def test_sweep_expired_sessions_none(monkeypatch, fake_redis):

    fake_redis.expired = []

    monkeypatch.setattr(
        ss,
        "redis_store",
        fake_redis,
    )

    monkeypatch.setattr(
        ss,
        "teardown_session",
        lambda session_id: None,
    )

    result = ss.sweep_expired_sessions()

    assert result == {
        "swept": 0,
        "failed": 0,
        "checked": 0,
    }