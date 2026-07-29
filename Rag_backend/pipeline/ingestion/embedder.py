import logging

from fastembed import TextEmbedding, SparseTextEmbedding

from Rag_backend.config.settings import settings

logger = logging.getLogger(__name__)


dense_model = TextEmbedding(model_name = settings.DENSE_EMBEDDING_MODEL)
sparse_model = SparseTextEmbedding(model_name=settings.SPARSE_EMBEDDING_MODEL)



def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Takes chunker.py's output, returns dense + sparse vectors per chunk in
    the exact shape qdrant_store.upsert_chunks() expects.
    """
    texts = [c["text"] for c in chunks]
 
    dense_vectors = [v.tolist() for v in dense_model.embed(texts)]
    sparse_results = list(sparse_model.embed(texts))
 
    embeddings = []
    for sparse in sparse_results:
        embeddings.append({
            "indices": sparse.indices.tolist(),
            "values": sparse.values.tolist(),
        })
 
    logger.info(f"[embedder] embedded {len(chunks)} chunks")
 
    return [
        {"dense": dense_vectors[i], "sparse": {idx: val for idx, val in zip(embeddings[i]["indices"], embeddings[i]["values"])}}
        for i in range(len(chunks))
    ]