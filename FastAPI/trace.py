import logging
from fastapi import APIRouter, HTTPException

from Rag_backend.data_stores.redis_store import redis_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trace", tags=["trace"])


@router.get("/{session_id}/latest")
def get_latest_trace(session_id: str):
    trace = redis_store.get_latest_trace(session_id)
    if trace is None:
        raise HTTPException(404, "no trace found for this session")
    return {"session_id": session_id, "trace": trace} 