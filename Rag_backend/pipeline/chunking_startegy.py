import logging
import re
import uuid
 
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
 
from Rag_backend.config.settings import settings
from Rag_backend.data_stores.redis_store import redis_store
 
logger = logging.getLogger(__name__)
 
TAG_RE = re.compile(r"<<<EL(\d+)>>>")

def tag_elements(elements: list[dict]) -> str:
    """Joins elements into one string, each prefixed with a locatable
    marker so we can recover page_number/bbox after splitting."""
    return "\n".join(f"<<<EL{i}>>>{e['text']}" for i, e in enumerate(elements))

def untag_chunk(chunk_text: str, elements: list[dict], index: int) -> dict:
    """Strips markers from a split chunk and resolves its position
    metadata from whichever original elements it covers."""
    covered = [int(m) for m in TAG_RE.findall(chunk_text)]
    clean_text = TAG_RE.sub("", chunk_text).strip()
 
    first_el = elements[covered[0]] if covered else elements[0]
    last_el = elements[covered[-1]] if covered else elements[0]
 
    return {
        "chunk_id": str(uuid.uuid4()),
        "chunk_index": index,
        "text": clean_text,
        "page_number": first_el["page_number"],
        "page_number_end": last_el["page_number"],
        "bbox": first_el["bbox"],
    }
 

def split_and_map(elements: list[dict], splitter) -> list[dict]:
    tagged_text = tag_elements(elements)
    raw_chunks = splitter.split_text(tagged_text)
    return [untag_chunk(text, elements, i) for i, text in enumerate(raw_chunks)]
 
 
def chunk_fixed_size(elements: list[dict], max_tokens: int = 300) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=max_tokens, chunk_overlap=0,
    )
    return split_and_map(elements, splitter)


def chunk_recursive_token(elements: list[dict], max_tokens: int = 400, overlap_tokens: int = 50) -> list[dict]:
    """Default strategy — LangChain's recursive splitter with overlap."""
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=max_tokens, chunk_overlap=overlap_tokens,
    )
    return split_and_map(elements, splitter)
 

def chunk_semantic(elements: list[dict]) -> list[dict]:
    splitter = SemanticChunker(
        HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
    )
    return split_and_map(elements, splitter)


STRATEGIES = {
    "fixed_size": chunk_fixed_size,
    "recursive_token": chunk_recursive_token,
    "semantic": chunk_semantic,
}

def resolve_strategy(chosen: str | None, session_id: str | None)-> str:
    """
    session-scoped uploads : the first upload's strategy(chosen, or default if none given)
    get locked in Redis. Every later upload in the same session ignores 'chosen' and reuses the locked value
    
    """

    if session_id:
        locked = redis_store.get_active_chunking_strategy(session_id)
        if locked:
            return locked
        
    strategy_name = chosen if chosen in STRATEGIES else settings.CHUNKING_STRATEGY

    if strategy_name not in STRATEGIES:
        raise ValueError(f"[chunker_strategy] unknown strategy: {strategy_name}")
    
    return strategy_name


def chunk_document(elements: list[dict], strategy_name: str) -> list[dict]:
    strategy_fn = STRATEGIES[strategy_name]
    chunks = strategy_fn(elements)
    logger.info(f"[chunker_strategy] {strategy_name} produced {len(chunks)} chunks")
    return chunks