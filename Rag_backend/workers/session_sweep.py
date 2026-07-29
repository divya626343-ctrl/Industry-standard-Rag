import logging
from celery import shared_task
from Rag_backend.data_stores.redis_store import redis_store, collection_name

from Rag_backend.data_stores.qdrant_store import vector_store  # your Qdrant/Weaviate wrapper — delete_collection(name)

logger = logging.getLogger(__name__)


def teardown_session(session_id: str) -> None:
    """Shared cleanup logic used by BOTH the explicit-signal path and the sweep fallback."""
    collection = collection_name(session_id)
    qdrant_error = None

    try:
        vector_store.delete_collection(collection)
        logger.info(f"[teardown] deleted vector collection={collection} session={session_id}")
    except Exception as e:
        qdrant_error = e
        logger.error(f"[teardown] FAILED to delete collection={collection} session={session_id} | {e}")

    redis_store.cleanup_session(session_id)
    logger.info(f"[teardown] Redis state cleared for session={session_id}")

    if qdrant_error:
        raise qdrant_error


def end_session_now(session_id: str) -> None:
    logger.info(f"[teardown] explicit end-session signal received | session={session_id}")
    teardown_session(session_id)



@shared_task(name="sweep_expired_sessions")
def sweep_expired_sessions() -> dict:
    expired_ids = redis_store.get_expired_sessions()  # inactivity > SESSION_TTL_MINUTES (30 min)

    swept, failed = 0, 0
    for session_id in expired_ids:
        try:
            teardown_session(session_id)
            swept += 1
        except Exception as e:
            failed += 1
            logger.error(f"[sweep] failed to tear down session={session_id} | {e}")

    logger.info(f"[sweep] run complete | swept={swept} failed={failed} checked={len(expired_ids)}")
    return {"swept": swept, "failed": failed, "checked": len(expired_ids)}