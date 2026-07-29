from celery import Celery
from Rag_backend.config.settings import settings

app = Celery(
    "rag_backend",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
     include=[
        "Rag_backend.workers.ingestion",
        "Rag_backend.workers.session_sweep",
    ],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


app.conf.beat_schedule = {
    "sweep-expired-sessions": {
        "task": "sweep_expired_sessions",
        "schedule": settings.SESSION_SWEEP_INTERVAL_SECONDS,
    },
}
# noqa: E402,F401