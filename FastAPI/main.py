import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from Rag_backend.config.settings import settings
from Rag_backend.data_stores.redis_store import redis_client
from Rag_backend.data_stores.qdrant_store import vector_store
from FastAPI import session, ingestion, documents, chunking, query, trace

logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Platform API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session.router)
app.include_router(ingestion.router)
app.include_router(documents.router)
app.include_router(documents.documents_router)
app.include_router(chunking.router)
app.include_router(query.router)
app.include_router(trace.router)



@app.get("/health")
def health_check():
    """Checks Redis + Qdrant reachability — for Docker/K8s liveness probes (NFR-15)."""
    status = {"redis": "unknown", "qdrant": "unknown"}
    healthy = True

    try:
        redis_client.ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {e}"
        healthy = False

    try:
        vector_store.client.get_collections()
        status["qdrant"] = "ok"
    except Exception as e:
        status["qdrant"] = f"error: {e}"
        healthy = False

    return {"status": "ok" if healthy else "degraded", "checks": status}



