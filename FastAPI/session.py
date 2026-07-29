import logging
import uuid
from fastapi import APIRouter, HTTPException

from Rag_backend.data_stores.redis_store import redis_store
from Rag_backend.session import create_session
from Rag_backend.workers.session_sweep import end_session_now

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/session", tags=["session"])


@router.post("/init")
def init_session():
    session_id = create_session()
    return {"session_id": session_id}


@router.get("/{session_id}/status")
def session_status(session_id: str):
    
    ttl_remaining = redis_store.get_session_ttl(session_id)

    if ttl_remaining is None or ttl_remaining <= 0:
        raise HTTPException(404, "session expired or not found")

    return {"session_id": session_id, "ttl_seconds": ttl_remaining}



@router.post("/{session_id}/end")
def end_session(session_id: str):
    end_session_now(session_id)
    return {"status": "ended"}