import pytest

from Rag_backend.graph import build_graph as bg


class FakeCompiledGraph:
    pass


class FakeStateGraph:
    instances = []

    def __init__(self, state_type):
        self.state_type = state_type
        self.nodes = {}
        self.edges = []
        self.conditional_edges = []
        self.compiled_with = None
        self.compile_result = FakeCompiledGraph()
        FakeStateGraph.instances.append(self)

    def add_node(self, name, fn):
        self.nodes[name] = fn

    def add_edge(self, from_node, to_node):
        self.edges.append((from_node, to_node))

    def add_conditional_edges(self, from_node, router_fn, mapping):
        self.conditional_edges.append((from_node, router_fn, mapping))

    def compile(self, checkpointer=None):
        self.compiled_with = checkpointer
        return self.compile_result


class FakeRedisSaver:
    def __init__(self, redis_client):
        self.redis_client = redis_client


@pytest.fixture
def built(monkeypatch):
    FakeStateGraph.instances = []

    monkeypatch.setattr(bg, "StateGraph", FakeStateGraph)
    monkeypatch.setattr(bg, "RedisSaver", FakeRedisSaver)
    monkeypatch.setattr(bg.redis, "from_url", lambda url: f"FAKE_REDIS_CLIENT:{url}")
    monkeypatch.setattr(bg.settings, "REDIS_URL", "redis://fake:6379/0")

    compiled = bg.build_graph()
    graph = FakeStateGraph.instances[0]

    return graph, compiled


def test_all_nodes_registered_with_correct_functions(built):
    graph, _ = built

    expected_nodes = {
        "rewrite_query": bg.rewrite_query,
        "content_safety": bg.content_safety,
        "topic_boundary_check": bg.topic_boundary_check,
        "query_encode": bg.query_encode,
        "retriever": bg.retriever,
        "fuse": bg.fuse,
        "cross_encoder": bg.cross_encoder,
        "sufficiency_gate": bg.sufficiency_gate,
        "generation": bg.generation,
        "hallucination_check": bg.hallucination_check,
        "PII": bg.PII,
        "answer_relevance_check": bg.answer_relevance_check,
        "trace_writer": bg.trace_writer,
    }

    assert graph.nodes == expected_nodes


def test_direct_edges(built):
    graph, _ = built

    expected_edges = [
        (bg.START, "rewrite_query"),
        ("rewrite_query", "content_safety"),
        ("fuse", "cross_encoder"),
        ("cross_encoder", "sufficiency_gate"),
        ("generation", "hallucination_check"),
        ("trace_writer", bg.END),
    ]

    assert graph.edges == expected_edges


def test_conditional_edges(built):
    graph, _ = built

    expected_conditional_edges = [
        (
            "content_safety",
            bg.after_safety_check,
            {"trace_writer": "trace_writer", "topic_boundary_check": "topic_boundary_check"},
        ),
        (
            "topic_boundary_check",
            bg.after_topic_boundary_check,
            {"trace_writer": "trace_writer", "query_encode": "query_encode"},
        ),
        (
            "query_encode",
            bg.after_query_encode,
            {"trace_writer": "trace_writer", "retriever": "retriever"},
        ),
        (
            "retriever",
            bg.after_retriever,
            {"trace_writer": "trace_writer", "fuse": "fuse"},
        ),
        (
            "sufficiency_gate",
            bg.after_sufficiency_gate,
            {"trace_writer": "trace_writer", "generation": "generation"},
        ),
        (
            "hallucination_check",
            bg.after_hallucination,
            {"generation": "generation", "PII": "PII", "trace_writer": "trace_writer"},
        ),
        (
            "PII",
            bg.after_PII,
            {"trace_writer": "trace_writer", "answer_relevance_check": "answer_relevance_check"},
        ),
        (
            "answer_relevance_check",
            bg.after_answer_relevance_check,
            {"rewrite_query": "rewrite_query", "trace_writer": "trace_writer"},
        ),
    ]

    assert graph.conditional_edges == expected_conditional_edges


def test_compiled_with_redis_checkpointer(built):
    graph, compiled = built

    assert isinstance(graph.compiled_with, FakeRedisSaver)
    assert graph.compiled_with.redis_client == "FAKE_REDIS_CLIENT:redis://fake:6379/0"
    assert compiled is graph.compile_result


def test_build_graph_returns_compiled_graph(built):
    _, compiled = built

    assert isinstance(compiled, FakeCompiledGraph)