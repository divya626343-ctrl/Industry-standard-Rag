import json 
import time
import redis
from Rag_backend.config.settings import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses = True)

HISTORY_KEEP_RECENT = 5
MAX_TRACE_ENTRIES = 50
MAX_TRACE_RUNS = 10 


def ttl_seconds()-> int:
    return settings.SESSION_TTL_MINUTES*60

def collection_name(session_id = None )-> str:
    """
    Deterministic collection/namespace name — no storage or lookup needed.
    Pass None (or omit) to get the shared/main corpus collection name.
    """

    if session_id is None:
        return settings.MAIN_COLLECTION_NAME
    return f"{settings.SESSION_COLLECTION_PREFIX}{session_id}"


class RedisStore:

    def register_session(self, session_id: str) -> None:
        """call once when a new session/brower tab starts"""
        now = time.time()
        redis_client.sadd("session:active", session_id)
        redis_client.hset(f"session:{session_id}:meta", mapping ={
            "created_at": now,
            "last_active": now,
        })

    def heartbeat(self, session_id: str)-> None:
        """call whenever a message is processed to reset the inactivity clock"""
        redis_client.hset(f"session:{session_id}:meta", "last_active", time.time())

    
    def get_expired_sessions(self)-> list[str]:
        """used by the background sweep job - inactivity > session_ttl_minutes"""
        expired = []
        ttl = ttl_seconds()
        now = time.time()
        for session_id in redis_client.smembers("session:active"):
            meta = redis_client.hgetall(f"session:{session_id}:meta")
            last_active = float(meta.get("last_active", 0))
            if now-last_active > ttl:
                expired.append(session_id)

        return expired

    def get_session_ttl(self, session_id: str) -> int | None:
    
        meta = redis_client.hgetall(f"session:{session_id}:meta")
        if not meta or "last_active" not in meta:
            return None

        last_active = float(meta["last_active"])
        remaining = ttl_seconds() - (time.time() - last_active)

        return max(0, int(remaining))
    
    def cleanup_session(self, session_id: str)-> None:
        """
        Deletes ALL Redis state for a session (history, metadata, chunking
        strategy, traces, session-scoped parent chunks). The caller (sweep job
        or explicit end-session handler) is responsible for separately
        deleting the session's vector collection via collection_name(session_id).
        
        """

        keys_to_delete = [
            f"session:{session_id}:meta",
            f"session:{session_id}:chunking_strategy",
            f"session:{session_id}:doc_summaries",
            f"history:{session_id}",
            f"trace:{session_id}"
        ]

        redis_client.delete(*keys_to_delete)
        redis_client.srem("session:active", session_id)

        for key in redis_client.scan_iter(match = f"parent:session:{session_id}:*"):
            redis_client.delete(key)




    def set_active_chunking_strategy(self, session_id: str, strategy: str) -> None:
            """
            Called by the Celery worker once it finishes chunking+embedding a
            user-uploaded document, so the rest of the pipeline knows which
            strategy produced the chunks currently sitting in this session's
            vector collection.
            """
            redis_client.set(f"session:{session_id}:chunking_strategy", strategy)
    
    def get_active_chunking_strategy(self, session_id: str) -> str | None:
            return redis_client.get(f"session:{session_id}:chunking_strategy")


    def load_history(self, session_id:str)-> dict:
        raw = redis_client.get(f"history:{session_id}")
        return json.loads(raw) if raw else{"messages": [], "summary": None}


    def save_history(self, session_id: str, history: dict)-> None:
        redis_client.set(f"history:{session_id}", json.dumps(history), ex = ttl_seconds())

    def get_context_for_query(self, session_id: str, summarizer_fn)-> tuple[str | None, list[dict]]:
        """summarizer_fn: callable(existing_summary, new messages)"""
        history = self.load_history(session_id)
        messages = history["messages"]
        summary = history["summary"]

        if len(messages)<= HISTORY_KEEP_RECENT:
            return summary, messages
        to_fold = messages[:-HISTORY_KEEP_RECENT]
        recent = messages[-HISTORY_KEEP_RECENT:]
        new_summary = summarizer_fn(summary, to_fold)

        self.save_history(session_id, {"messages": recent, "summary": new_summary})

        return new_summary, recent
    

    def append_turn(self, session_id: str, role: str, content:str)-> None:
        history = self.load_history(session_id)
        history["messages"].append({"role": role, "content": content, "timestamp": time.time()})

        self.save_history(session_id, history)
    

    def append_trace(self, session_id: str, trace_record: list[dict]) -> None:
        key = f"trace:{session_id}"
        redis_client.rpush(key, json.dumps(trace_record))
        redis_client.ltrim(key, -MAX_TRACE_RUNS, -1)
        redis_client.expire(key, ttl_seconds())

    def get_latest_trace(self, session_id: str) -> list[dict] | None:
        key = f"trace:{session_id}"
        raw = redis_client.lindex(key, -1)
        return json.loads(raw) if raw else None

    def get_traces(self, session_id: str) -> list[dict]:
        raw_list = redis_client.lrange(f"trace:{session_id}", 0, -1)
        return [json.loads(r) for r in raw_list]


    def set_parent_chunk(self, chunk_id: str, text: str, session_id: str | None = None) -> None:
        if session_id:
            redis_client.set(f"parent:session:{session_id}:{chunk_id}", text, ex=ttl_seconds())
        else:
            redis_client.set(f"parent:shared:{chunk_id}", text)  # no TTL — main corpus is persistent


    def get_parent_chunk(self, chunk_id: str, session_id: str | None = None) -> str | None:
        if session_id:
            return redis_client.get(f"parent:session:{session_id}:{chunk_id}")
        return redis_client.get(f"parent:shared:{chunk_id}")

    def add_doc_topic_summary(self, session_id: str, doc_id: str, summary: str) -> None:
        key = f"session:{session_id}:doc_summaries"
        redis_client.hset(key, doc_id, summary)
        redis_client.expire(key, ttl_seconds())  # hset doesn't support ex inline, set separately

    def get_doc_topic_summaries(self, session_id: str) -> list[str]:
       key = f"session:{session_id}:doc_summaries"
       return list(redis_client.hgetall(key).values())

    def add_content_hash(self, session_id: str, content_hash: str) -> None:
        key = f"session:{session_id}:content_hashes"
        redis_client.sadd(key, content_hash)
        redis_client.expire(key, ttl_seconds())

    def has_content_hash(self, session_id: str, content_hash: str) -> bool:
        key = f"session:{session_id}:content_hashes"
        return redis_client.sismember(key, content_hash)
    
redis_store = RedisStore()