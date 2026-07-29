from Rag_backend.nodes.answer_relevance_check import answer_relevance_check
from Rag_backend.nodes.content_safety import content_safety
from Rag_backend.nodes.cross_encoder import cross_encoder
from Rag_backend.nodes.fuse import fuse
from Rag_backend.nodes.generation import generation
from Rag_backend.nodes.hallucination_check import hallucination_check
from Rag_backend.nodes.pii_detection import PII
from Rag_backend.nodes.query_encoder import query_encode
from Rag_backend.nodes.query_rewriter import rewrite_query
from Rag_backend.nodes.retriever import retriever
from Rag_backend.nodes.sufficiency_gate import sufficiency_gate
from Rag_backend.nodes.topic_boundary_check import topic_boundary_check
from Rag_backend.nodes.trace_writer import trace_writer
from Rag_backend.config.settings import settings
from Rag_backend.graph.state import State
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.redis import RedisSaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
import redis
import redis.asyncio as aioredis
from Rag_backend.graph.router import (
    after_answer_relevance_check,
    after_hallucination,
    after_PII,
    after_query_encode,
    after_retriever,
    after_safety_check,
    after_sufficiency_gate,
    after_topic_boundary_check,
)


def _build_stategraph() -> StateGraph:
    """Shared node/edge wiring — used by both the sync and async builders
    so the graph topology only has to be defined once."""
    graph = StateGraph(State)

    graph.add_node("rewrite_query", rewrite_query)
    graph.add_node("content_safety", content_safety)
    graph.add_node("topic_boundary_check", topic_boundary_check)
    graph.add_node("query_encode", query_encode)
    graph.add_node("retriever", retriever)
    graph.add_node("fuse", fuse)
    graph.add_node("cross_encoder", cross_encoder)
    graph.add_node("sufficiency_gate", sufficiency_gate)
    graph.add_node("generation", generation)
    graph.add_node("hallucination_check", hallucination_check)
    graph.add_node("PII", PII)
    graph.add_node("answer_relevance_check", answer_relevance_check)
    graph.add_node("trace_writer", trace_writer)

    graph.add_edge(START, "rewrite_query")
    graph.add_edge("rewrite_query", "content_safety")

    graph.add_conditional_edges("content_safety", after_safety_check, {
        "trace_writer": "trace_writer",
        "topic_boundary_check": "topic_boundary_check",
    })

    graph.add_conditional_edges("topic_boundary_check", after_topic_boundary_check, {
        "trace_writer": "trace_writer",
        "query_encode": "query_encode",
    })

    graph.add_conditional_edges("query_encode", after_query_encode, {
        "trace_writer": "trace_writer",
        "retriever": "retriever",
    })

    graph.add_conditional_edges("retriever", after_retriever, {
        "trace_writer": "trace_writer",
        "fuse": "fuse",
    })

    graph.add_edge("fuse", "cross_encoder")
    graph.add_edge("cross_encoder", "sufficiency_gate")

    graph.add_conditional_edges("sufficiency_gate", after_sufficiency_gate, {
        "trace_writer": "trace_writer",
        "generation": "generation",
    })

    graph.add_edge("generation", "hallucination_check")

    graph.add_conditional_edges("hallucination_check", after_hallucination, {
        "generation": "generation",
        "PII": "PII",
        "trace_writer": "trace_writer",
    })

    graph.add_conditional_edges("PII", after_PII, {
        "trace_writer": "trace_writer",
        "answer_relevance_check": "answer_relevance_check",
    })

    graph.add_conditional_edges("answer_relevance_check", after_answer_relevance_check, {
        "rewrite_query": "rewrite_query",
        "trace_writer": "trace_writer",
    })

    graph.add_edge("trace_writer", END)
    return graph


def build_graph():
    """SYNC — used by run_query() (graph.invoke()). Uses sync RedisSaver."""
    graph = _build_stategraph()

    redis_client = redis.from_url(settings.REDIS_URL)
    checkpointer = RedisSaver(redis_client=redis_client)
    checkpointer.setup()

    return graph.compile(checkpointer=checkpointer)


async def build_graph_async():
    """ASYNC — used by run_query_streaming() (graph.astream()). Uses AsyncRedisSaver."""
    graph = _build_stategraph()

    redis_client = aioredis.from_url(settings.REDIS_URL)
    checkpointer = AsyncRedisSaver(redis_client=redis_client)
    await checkpointer.asetup()

    return graph.compile(checkpointer=checkpointer)