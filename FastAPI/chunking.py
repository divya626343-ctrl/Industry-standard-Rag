# FastAPI/routes/chunking_strategy.py
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from Rag_backend.data_stores.redis_store import redis_store
from Rag_backend.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/session/{session_id}/chunking-strategy", tags=["chunking-strategy"])


class ChunkingStrategyRequest(BaseModel):
    strategy: str


@router.get("")
def get_chunking_strategy(session_id: str):
    """Reports the locked strategy if one exists, else the default (unlocked)."""
    locked = redis_store.get_active_chunking_strategy(session_id)
    return {
        "strategy": locked or settings.DEFAULT_CHUNKING_STRATEGY,
        "locked": locked is not None,
    }


@router.post("")
def set_chunking_strategy(session_id: str, body: ChunkingStrategyRequest):
    """
    Locks the strategy on first call for this session. Subsequent calls
    are silently ignored (existing lock wins) — matches the 'locks on
    first upload or first query' rule; this endpoint just gives the
    frontend an explicit moment to set it before either happens.
    """
    existing = redis_store.get_active_chunking_strategy(session_id)
    if existing:
        return {"strategy": existing, "locked": True, "note": "already locked, ignoring new value"}

    redis_store.set_active_chunking_strategy(session_id, body.strategy)
    logger.info(f"[chunking-strategy] locked | session_id={session_id} strategy={body.strategy}")
    return {"strategy": body.strategy, "locked": True}