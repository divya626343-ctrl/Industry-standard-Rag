from Rag_backend.pipeline.chunking_startegy import resolve_strategy, chunk_document

import logging

logger = logging.getLogger(__name__)

def chunk_elements(
        elements: list[dict],
        chosen_strategy: str | None,
        session_id: str| None,
)-> tuple[list[dict], str]:
    
    """
    Thin entry point called by indexer.py. Resolves which strategy applies
    to this upload (respecting the session lock in chunker_strategy.py),
    runs it, and returns both the chunks and the resolved strategy name —
    indexer.py needs the name to persist it via
    redis_store.set_active_chunking_strategy() on a session's first upload.
    
    """

    strategy_name = resolve_strategy(chosen= chosen_strategy, session_id=session_id)

    chunks = chunk_document(elements, strategy_name)

    logger.info(f"[chunker] session = {session_id or 'shared'}"
                
                f"strategy = {strategy_name} chunks = {len(chunks)}"
                )
    
    return chunks, strategy_name