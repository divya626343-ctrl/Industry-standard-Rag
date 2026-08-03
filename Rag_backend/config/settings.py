from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM (Groq) ───────────────────────────────────────────
    GROQ_API_KEY: str = Field(default="", description="Groq API key")

    # Two models: cheap/fast for judging & guardrails, stronger for user-facing generation
    GROQ_MODEL_JUDGE: str = "llama-3.1-8b-instant"
    GROQ_MODEL_GENERATION: str = "llama-3.3-70b-versatile"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2048
    LLM_TIMEOUT: int = 30
    LLM_MAX_RETRIES: int = 3

    # Proactive rate limiter budgets (calls per minute, per task type)
    RATE_LIMIT_JUDGE_CALLS_PER_MIN: int = 60
    RATE_LIMIT_GENERATION_CALLS_PER_MIN: int = 30

    # ── Embeddings ───────────────────────────────────────────
    DENSE_EMBEDDING_MODEL : str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_MODEL : str = "BAAI/bge-large-en"
    SPARSE_EMBEDDING_MODEL : str = "Qdrant/bm25"
    EMBEDDING_BATCH_SIZE: int = 32

    # ── Chunking ─────────────────────────────────────────────
    CHUNKING_STRATEGY: str = "recursive_token"   # fixed_size, recursive_token, semantic
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 100
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.6
    HIERARCHICAL_PARENT_SIZE: int = 2048
    HIERARCHICAL_CHILD_SIZE: int = 256

    # ── Sparse retrieval (BM25) ──────────────────────────────
    SPARSE_BACKEND: str = "rank_bm25"     # rank_bm25 | elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # ── Vector store ─────────────────────────────────────────
    VECTOR_STORE_BACKEND: str = "qdrant"  # qdrant | weaviate
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_ENDPOINT: str = "http://localhost:6333"


    MAIN_COLLECTION_NAME: str = "shared_enterprise_corpus"
    SESSION_COLLECTION_PREFIX: str = "session_"
    
    # ── Object store ─────────────────────────────────────────
    OBJECT_STORE_ENDPOINT: str
    OBJECT_STORE_ACCESS_KEY: str
    OBJECT_STORE_SECRET_KEY: str
    OBJECT_STORE_BUCKET: str
    OBJECT_STORE_REGION: str  # e.g. "us-west-004" for B2
   

    # ── Hybrid retrieval & reranking ─────────────────────────
    RETRIEVAL_TOP_K : int = 25
    FUSE_TOP_K : int = 20 # top chunk in fusion 
    RRF_K: int = 60                       # RRF fusion constant
    RERANK_TOP_N: int = 15                 # final chunks passed to LLM after rerank
    RERANK_BACKEND: str = "cross_encoder" # cross_encoder | cohere
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ── Sufficiency gate ─────────────────────────────────────
    SUFFICIENCY_SCORE: float = 0.75
    ANSWER_RELEVANCE_THRESHOLD: float = 0.6

    # ── Guardrails ────────────────────────────────────────────
    HALLUCINATION_CHECK_ENABLED: bool = True
    PII_REDACTION_ENABLED: bool = True
    TOPIC_BOUNDARY_ENABLED: bool = True
    MAX_GUARDRAIL_RETRIES: int = 3       # retry generation on failed hallucination check

    # ── Session lifecycle (ephemeral, no-auth model) ─────────
    SESSION_TTL_MINUTES: int = 30
    SESSION_HEARTBEAT_SECONDS: int = 60
    SESSION_SWEEP_INTERVAL_SECONDS: int = 300

    # ── Async task queue ──────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    

    # ── Evaluation & experiment tracking ──────────────────────
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    GOLDEN_EVAL_SET_PATH: str = str(BASE_DIR / "evaluation" / "golden_eval_set.json")

    CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "https://urban-journey-x5gxqr5xqp9j2p45v-3000.app.github.dev/"]
    MAX_UPLOAD_SIZE_MB: int = 30


    GENERATION_LOCAL_RETRIES: int = 2
    RAGAS_FAITHFULNESS_THRESHOLD: float = 0.92
    RAGAS_CONTEXT_PRECISION_THRESHOLD: float = 0.88
    RAGAS_ANSWER_RELEVANCE_THRESHOLD: float = 0.90
    RETRIEVAL_MRR_THRESHOLD: float = 0.78

    # ── Observability (self-hosted Langfuse) ──────────────────
    TRACE_DIR: str = str(BASE_DIR / "traces")
    LOG_LEVEL: str = "info"

    #---corpus domain description ------------------------------

    CORPUS_DOMAIN_DESCRIPTION: str = (
    "This corpus covers ZX Bank's internal documentation: banking policies and "
    "procedures, deposit and loan account products, interest rates and fee "
    "structures, compliance and regulatory guidelines, customer service and "
    "support processes, and internal technical/operational documentation "
    "related to banking systems."
)

    # ── Ingestion ─────────────────────────────────────────────
    SUPPORTED_FILE_TYPES: list[str] = ["pdf", "docx", "html", "md","pptx"]
    INGESTION_TARGET_DOCS_PER_MIN: int = 100

    # ── API Server ────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True

    # ── Frontend ──────────────────────────────────────────────
    STREAMLIT_API_URL: str = "http://localhost:8000"

    # ── Properties ────────────────────────────────────────────
    @property
    def active_base_url(self) -> str:
        return self.GROQ_BASE_URL

    @property
    def active_api_key(self) -> str:
        return self.GROQ_API_KEY

    @property
    def redis_broker_url(self) -> str:
        return self.CELERY_BROKER_URL

    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self.REDIS_URL.rsplit("/", 1)[0] + "/1"

    # ── Validators ────────────────────────────────────────────
    @field_validator("LLM_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError("LLM_TEMPERATURE must be between 0.0 and 2.0")
        return v

    @field_validator(
        "SEMANTIC_SIMILARITY_THRESHOLD",
        "RAGAS_FAITHFULNESS_THRESHOLD",
        "RAGAS_CONTEXT_PRECISION_THRESHOLD",
        "RAGAS_ANSWER_RELEVANCE_THRESHOLD",
        "RETRIEVAL_MRR_THRESHOLD",
    )
    @classmethod
    def validate_thresholds(cls, v):
        if not 0.0 < v <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        return v

    def validate_api_keys(self) -> tuple[bool, str]:
        missing = []
        if not self.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")
        if self.RERANK_BACKEND == "cohere" and not self.COHERE_API_KEY:
            missing.append("COHERE_API_KEY")
        if missing:
            return False, f"[warning] missing keys: {', '.join(missing)}"
        return True, "all required API keys found"

    

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()