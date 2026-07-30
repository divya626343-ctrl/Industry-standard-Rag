import base64
import logging
from fastapi import APIRouter, UploadFile, Form, HTTPException

from Rag_backend.config.settings import settings
from Rag_backend.data_stores.redis_store import redis_store
from Rag_backend.pipeline.ingestion.parser import compute_content_hash
from Rag_backend.workers.ingestion import ingest_document_task
from Rag_backend.workers.celery_app import app as celery_app
from celery.result import AsyncResult

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ingestion"])

FORMAT_BY_EXTENSION = {
    ".pdf": "pdf", ".docx": "docx", ".pptx": "pptx"
}


def detect_format(filename: str) -> str:
    for ext, fmt in FORMAT_BY_EXTENSION.items():
        if filename.lower().endswith(ext):
            return fmt
    raise HTTPException(400, f"unsupported file type: {filename}")


@router.post("/upload")
async def upload_document(
    file: UploadFile,
    session_id: str = Form(...),
    org: str | None = Form(None),
    chosen_strategy: str | None = Form(None),
):
    file_format = detect_format(file.filename)
    file_bytes = await file.read()

    # size check — before any hashing/encoding/enqueueing work
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(413, f"file exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    # content-hash dedup — before enqueueing, so a duplicate never reaches Celery at all
    content_hash = compute_content_hash(file_bytes)
    if redis_store.has_content_hash(session_id, content_hash):
        logger.info(f"[upload] duplicate rejected before enqueue | session_id={session_id}")
        return {"status": "duplicate", "task_id": None}

    file_bytes_b64 = base64.b64encode(file_bytes).decode("utf-8")

    task = ingest_document_task.delay(
        file_bytes_b64=file_bytes_b64,
        file_format=file_format,
        filename=file.filename,
        org=org,
        session_id=session_id,
        chosen_strategy=chosen_strategy,
    )

    logger.info(f"[upload] enqueued | session_id={session_id} task_id={task.id}")
    return {"status": "queued", "task_id": task.id}


@router.get("/task-status/{task_id}")
def task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)

    response = {"task_id": task_id, "state": result.state}

    if result.state == "SUCCESS":
        response["result"] = result.result
    elif result.state == "FAILURE":
        response["error"] = str(result.result)

    return response