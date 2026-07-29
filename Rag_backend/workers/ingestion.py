import base64
import logging

from Rag_backend.workers.celery_app import app
from Rag_backend.pipeline.ingestion.indexer import ingest_document

logger = logging.getLogger(__name__)


@app.task(name="ingest_document_task", bind=True, max_retries=3, default_retry_delay=10)
def ingest_document_task(
    self,
    file_bytes_b64: str,
    file_format: str,
    filename: str,
    org: str | None = None,
    session_id: str | None = None,
    chosen_strategy: str | None = None,
) -> dict:
    """
    Thin Celery wrapper around indexer.ingest_document() — no logic of its
    own, just decodes the payload and delegates.
    """
    try:
        file_bytes = base64.b64decode(file_bytes_b64)

        result = ingest_document(
            file_bytes=file_bytes,
            file_format=file_format,
            filename=filename,
            org=org,
            session_id=session_id,
            chosen_strategy=chosen_strategy,
        )

        logger.info(f"[ingestion_task] completed | session_id={session_id} result={result}")
        return result

    except Exception as e:
        logger.error(
            f"[ingestion_task] attempt {self.request.retries + 1}/{self.max_retries + 1} "
            f"failed | session_id={session_id} | {e}"
        )
        raise self.retry(exc=e)