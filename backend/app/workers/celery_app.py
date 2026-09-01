from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "tenderguard",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # A dead broker must fail .delay() fast, not retry for 20+ seconds — the
    # API routes catch that failure and run ingestion inline instead, but
    # only if it fails quickly enough to still feel like one request.
    broker_connection_retry_on_startup=False,
    broker_connection_retry=False,
    broker_connection_timeout=2,
    broker_transport_options={"max_retries": 0},
)

celery_app.autodiscover_tasks(["app.workers"])
