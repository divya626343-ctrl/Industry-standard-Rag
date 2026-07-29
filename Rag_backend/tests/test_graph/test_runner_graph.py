import pytest

from Rag_backend.graph import runner_graph as rg


class FakeGraph:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []

    def invoke(self, state, config=None):
        self.calls.append({"state": state, "config": config})
        if self.exc:
            raise self.exc
        return self.result


class FakeRedisStore:
    def __init__(self):
        self.heartbeat_calls = []
        self.append_turn_calls = []

    def heartbeat(self, session_id):
        self.heartbeat_calls.append(session_id)

    def append_turn(self, session_id, role, content):
        self.append_turn_calls.append((session_id, role, content))


@pytest.fixture
def fake_redis_store(monkeypatch):
    store = FakeRedisStore()
    monkeypatch.setattr(rg, "redis_store", store)
    return store


@pytest.fixture
def fake_initial_state(monkeypatch):
    captured = {}

    def fake_create_initial_state(session_id, query):
        state = {"session_id": session_id, "query": query, "trace_log": []}
        captured["state"] = state
        return state

    monkeypatch.setattr(rg, "create_initial_state", fake_create_initial_state)
    return captured


def test_run_query_success(monkeypatch, fake_redis_store, fake_initial_state):

    fake_graph = FakeGraph(
        result={
            "final_answer": "The retention period is 90 days.",
            "citations": {"doc1": ["page 3"]},
        }
    )
    monkeypatch.setattr(rg, "graph", fake_graph)

    result = rg.run_query("What is the retention period?", "sess-123")

    assert result == {
        "answer": "The retention period is 90 days.",
        "citations": {"doc1": ["page 3"]},
        "exit_stage": None,
    }

    assert fake_redis_store.heartbeat_calls == ["sess-123"]
    assert fake_redis_store.append_turn_calls == [
        ("sess-123", "user", "What is the retention period?"),
        ("sess-123", "assistant", "The retention period is 90 days."),
    ]

    assert fake_graph.calls[0]["state"] is fake_initial_state["state"]
    assert fake_graph.calls[0]["config"] == {"configurable": {"thread_id": "sess-123"}}


def test_run_query_exit_stage_with_exit_message(monkeypatch, fake_redis_store, fake_initial_state):

    fake_graph = FakeGraph(
        result={
            "exit_stage": "topic_boundary",
            "exit_message": "I don't have information about that in the documents I have access to.",
        }
    )
    monkeypatch.setattr(rg, "graph", fake_graph)

    result = rg.run_query("What's the weather?", "sess-123")

    assert result == {
        "answer": "I don't have information about that in the documents I have access to.",
        "citations": {},
        "exit_stage": "topic_boundary",
    }

    assert fake_redis_store.append_turn_calls == [
        ("sess-123", "user", "What's the weather?"),
        (
            "sess-123",
            "assistant",
            "I don't have information about that in the documents I have access to.",
        ),
    ]


def test_run_query_exit_stage_without_exit_message(monkeypatch, fake_redis_store, fake_initial_state):

    fake_graph = FakeGraph(result={"exit_stage": "sufficiency_gate_error"})
    monkeypatch.setattr(rg, "graph", fake_graph)

    result = rg.run_query("query text", "sess-123")

    assert result["answer"] == "I couldn't process that request."
    assert result["exit_stage"] == "sufficiency_gate_error"
    assert result["citations"] == {}


def test_run_query_missing_final_answer_and_citations(monkeypatch, fake_redis_store, fake_initial_state):

    fake_graph = FakeGraph(result={})
    monkeypatch.setattr(rg, "graph", fake_graph)

    result = rg.run_query("query text", "sess-123")

    assert result == {
        "answer": "I couldn't generate an answer.",
        "citations": {},
        "exit_stage": None,
    }
    assert fake_redis_store.append_turn_calls[-1] == (
        "sess-123",
        "assistant",
        "I couldn't generate an answer.",
    )


def test_run_query_graph_invocation_exception(monkeypatch, fake_redis_store, fake_initial_state):

    fake_graph = FakeGraph(exc=RuntimeError("checkpointer unavailable"))
    monkeypatch.setattr(rg, "graph", fake_graph)

    result = rg.run_query("query text", "sess-123")

    assert result == {
        "answer": "we ran into an issue processing your request. Please try again.",
        "citations": {},
        "exit_stage": "graph_invocation_error",
    }

   
    assert fake_redis_store.heartbeat_calls == ["sess-123"]

   
    assert fake_redis_store.append_turn_calls == []