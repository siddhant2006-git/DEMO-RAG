import uuid

from app.core.broker_check import is_redis_reachable
from app.core.logging import get_logger

logger = get_logger(__name__)


def enqueue_ingestion(document_id: str) -> None:
    """Enqueues ingestion on the Celery worker when Redis is reachable;
    otherwise runs it inline in the request. A fast socket probe decides
    this up front rather than letting Celery's own connection-retry logic
    run (which can take many seconds even when told not to retry) — the
    point is that an upload completes promptly either way, worker running
    or not.
    """
    if is_redis_reachable():
        from app.workers.tasks import ingest_document_task

        ingest_document_task.delay(document_id)
        return

    logger.info("redis_unreachable_running_ingestion_inline", document_id=document_id)
    from app.db.session import SessionLocal
    from app.models.document import Document
    from app.services.ingestion.pipeline import ingest_document

    db = SessionLocal()
    try:
        document = db.get(Document, uuid.UUID(document_id))
        if document is not None:
            ingest_document(db, document)
    finally:
        db.close()
