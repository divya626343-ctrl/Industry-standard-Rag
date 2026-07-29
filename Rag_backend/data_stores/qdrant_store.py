import logging
from qdrant_client import QdrantClient, models
from Rag_backend.config.settings import settings

logger = logging.getLogger(__name__)

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"


class QdrantStore:
    def __init__(self):
        self.client = QdrantClient(url = settings.QDRANT_ENDPOINT)
    
    def collection_exists(self, collection_name: str)->bool:
        return self.client.collection_exists(collection_name)
    
    def create_collection(self, collection_name: str, dense_vector_size: int)-> None:
        if self.collection_exists(collection_name):
            logger.debug(f"[qdrant] collection already exists:{collection_name}")

        self.client.create_collection(
            collection_name= collection_name,
            vectors_config={
                DENSE_VECTOR_NAME: models.VectorParams(
                    size = dense_vector_size,
                    distance=models.Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: models.SparseVectorParams(),
            }
        )

        logger.info(f"[qdrant] created collection: {collection_name} (dim = {dense_vector_size})")



    def delete_collection(self, collection_name: str)-> None:
        """
        called on session teardown or admin-triggered corpus reindex
        
        """
        if not self.client.collection_exists(collection_name):
            logger.debug(f"[qdrant] delete skipped, collection doesn't exists: {collection_name}")

            return 
        
        self.client.delete_collection(collection_name)

        logger.info(f"[qdrant] deleted collection: {collection_name}")


    def upsert_chunks(
            self,
            collection_name: str,
            chunk_ids: list[str],
            dense_vectors: list[list[float]],
            sparse_vectors: list[dict[int, float]],
            payloads: list[dict],
    )-> None:
        """
        payload should carry whatever metadata is returned e.g. {"doc_id", "text":..., "parent_id":...}
        
        """

        points = []

        for chunk_id, dense_vec, sparse_vec, payload in zip(
                chunk_ids,
                dense_vectors,
                sparse_vectors,
                payloads,
            ):
            points.append(
                models.PointStruct(
                    id = chunk_id,
                    vector = {
                        DENSE_VECTOR_NAME: dense_vec,
                        SPARSE_VECTOR_NAME: models.SparseVector(
                            indices = list(sparse_vec.keys()),
                            values = list(sparse_vec.values()),
                        ),
                    },

                    payload = payload,
                )
            )

        self.client.upsert(
                collection_name=collection_name,
                points=points,
            )
        logger.debug(f"[qdrant] upserted {len(points)} chunks into {collection_name}")




    def search_hybrid(
        self,
        collection_name: str,
        dense_query_vector: list[float],
        sparse_query_vector: dict[int, float],
        top_k: int | None = None,
        query_filter: models.Filter | None = None,
    )-> list[dict]:
        
        """
        Runs dense + sparse search in parallel  and fuses them server-side via
        qdrant's native rrf(recipocal rank fusion) - this is the hybrid 
        retrieval step, for a single collection.
        
        """

        if not self.collection_exists(collection_name):
            return []
        
        top_k = top_k or settings.RETRIEVAL_TOP_K

        result = self.client.query_points(
            collection_name=collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_query_vector,
                    using=DENSE_VECTOR_NAME,
                    limit=top_k,
                    filter=query_filter,
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=list(sparse_query_vector.keys()),
                        values=list(sparse_query_vector.values()),
                    ),
                    using=SPARSE_VECTOR_NAME,
                    limit=top_k,
                    filter=query_filter,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
        )

        return [
            {"chunk_id": point.id, "score": point.score, "payload": point.payload} for point in result.points
        ] 
    

    def search_dense_only(
        self,
        collection_name: str,
        dense_query_vector: list[float],
        top_k: int | None = None,
        query_filter: models.Filter | None = None,
    ) -> list[dict]:
        """Fallback for collections/cases where sparse vectors aren't populated."""
        if not self.collection_exists(collection_name):
            return []
 
        top_k = top_k or settings.RETRIEVAL_TOP_K
        result = self.client.query_points(
            collection_name=collection_name,
            query=dense_query_vector,
            using=DENSE_VECTOR_NAME,
            limit=top_k,
            query_filter=query_filter,
        )
        return [
            {"chunk_id": point.id, "score": point.score, "payload": point.payload}
            for point in result.points
        ]

    def get_chunk_payload(self, chunk_id: str, collection_name: str)-> dict | None:
        points = self.client.retrieve(collection_name=collection_name, ids=[chunk_id], with_payload= True)
        return points[0].payload if points else None




vector_store = QdrantStore()
        