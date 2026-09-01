import uuid

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.ingestion.pipeline import ingest_document
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="ingestion.ingest_document", bind=True, max_retries=2)
def ingest_document_task(self, document_id: str) -> str:
    db = SessionLocal()
    try:
        document = db.get(Document, uuid.UUID(document_id))
        if document is None:
            logger.error("ingest_task_document_missing", document_id=document_id)
            return "missing"
        ingest_document(db, document)
        return document.status
    finally:
        db.close()
