
import uuid
from Rag_backend.data_stores.redis_store import redis_store

def create_session() -> str:
    session_id = str(uuid.uuid4())
    redis_store.register_session(session_id)
    return session_id