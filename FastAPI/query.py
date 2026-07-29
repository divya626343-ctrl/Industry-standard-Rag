import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from Rag_backend.graph.runner_graph_streaming import run_query_streaming

logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"])


def _to_sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@router.post("/query")
async def query(query: str, session_id: str):
    """
    SSE endpoint — streams status updates, then a final 'done' or 'error'
    event. run_query_streaming handles all Redis writes (heartbeat,
    conversation turns, trace save) internally; this route only serializes
    its yielded dicts to the SSE wire format.
    """
    async def event_generator():
        async for event in run_query_streaming(query=query, session_id=session_id):
            yield _to_sse(event)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
