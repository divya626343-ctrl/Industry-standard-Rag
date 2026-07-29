import pytest

from Rag_backend.nodes import trace_writer as tw


class FakeRedisStore:
    def __init__(self, fail_on_call=None, fail_error=None):
        self.calls = []
        self.fail_on_call = fail_on_call
        self.fail_error = fail_error

    def append_trace(self, session_id, entry):
        call_number = len(self.calls) + 1
        if self.fail_on_call is not None and call_number == self.fail_on_call:
            raise (self.fail_error or RuntimeError("redis unavailable"))
        self.calls.append((session_id, entry))


@pytest.fixture
def base_state():
    return {
        "session_id": "sess-123",
        "trace_log": [
            {"node": "content_safety", "event": "passed"},
            {"node": "topic_boundary_check", "event": "passed"},
        ],
    }


def test_trace_writer_persists_all_entries(monkeypatch, base_state):

    fake_store = FakeRedisStore()
    monkeypatch.setattr(tw, "redis_store", fake_store)

    result = tw.trace_writer(base_state)

    assert fake_store.calls == [
        ("sess-123", {"node": "content_safety", "event": "passed"}),
        ("sess-123", {"node": "topic_boundary_check", "event": "passed"}),
    ]
    assert result is base_state


def test_trace_writer_no_session_id_skips_persistence(monkeypatch, base_state):

    base_state["session_id"] = None
    fake_store = FakeRedisStore()
    monkeypatch.setattr(tw, "redis_store", fake_store)

    result = tw.trace_writer(base_state)

    assert fake_store.calls == []
    assert result is base_state


def test_trace_writer_empty_trace_log(monkeypatch, base_state):

    base_state["trace_log"] = []
    fake_store = FakeRedisStore()
    monkeypatch.setattr(tw, "redis_store", fake_store)

    result = tw.trace_writer(base_state)

    assert fake_store.calls == []
    assert result is base_state


def test_trace_writer_missing_trace_log_key(monkeypatch):

    state = {"session_id": "sess-123"}
    fake_store = FakeRedisStore()
    monkeypatch.setattr(tw, "redis_store", fake_store)

    result = tw.trace_writer(state)

    assert fake_store.calls == []
    assert result is state


def test_trace_writer_exception_is_swallowed_and_partial_writes_persist(monkeypatch, base_state):

    fake_store = FakeRedisStore(fail_on_call=2, fail_error=RuntimeError("redis unavailable"))
    monkeypatch.setattr(tw, "redis_store", fake_store)

    result = tw.trace_writer(base_state)

    # first entry was persisted before the second call raised
    assert fake_store.calls == [
        ("sess-123", {"node": "content_safety", "event": "passed"}),
    ]

    
    assert result is base_state
    assert "exit_stage" not in result
    assert "exit_message" not in result