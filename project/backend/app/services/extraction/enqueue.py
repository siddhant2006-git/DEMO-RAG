import threading
import uuid

from app.core.broker_check import is_redis_reachable
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Guards the inline (no-worker) path only: without Redis, extraction runs
# synchronously in the request thread, and a single Ollama instance
# processes one generation at a time — a second click before the first
# finishes doesn't queue behind it, it runs concurrently and both requests
# end up starved, timing out client and server side alike. This blocks a
# duplicate inline run for the same tender/bid instead of silently piling
# both onto Ollama.
_inline_lock = threading.Lock()
_inline_in_progress: set[str] = set()


def _begin_inline(key: str) -> None:
    with _inline_lock:
        if key in _inline_in_progress:
            raise AppError(
                "EXTRACTION_IN_PROGRESS",
                "Extraction is already running for this document — wait for it to finish before retrying.",
                409,
            )
        _inline_in_progress.add(key)


def _end_inline(key: str) -> None:
    with _inline_lock:
        _inline_in_progress.discard(key)


def run_or_enqueue_requirement_extraction(tender_id: str) -> tuple[str, int | None]:
    """Runs tender-requirement extraction on the Celery worker when Redis is
    reachable, otherwise inline in the request — same enqueue-or-inline
    pattern as ingestion (services/ingestion/enqueue.py), so extraction is
    reachable from the API with no worker required for the demo to work.

    Returns (status, requirements_created): status is "queued" when
    dispatched (the count isn't known yet) or "done" when it ran inline.
    """
    if is_redis_reachable():
        from app.workers.tasks import extract_tender_requirements_task

        extract_tender_requirements_task.delay(tender_id)
        return "queued", None

    logger.info("redis_unreachable_running_extraction_inline", tender_id=tender_id)
    key = f"tender:{tender_id}"
    _begin_inline(key)
    try:
        return "done", extract_tender_requirements(tender_id)
    finally:
        _end_inline(key)


def run_or_enqueue_fact_extraction(bid_id: str) -> tuple[str, int | None]:
    if is_redis_reachable():
        from app.workers.tasks import extract_bid_facts_task

        extract_bid_facts_task.delay(bid_id)
        return "queued", None

    logger.info("redis_unreachable_running_extraction_inline", bid_id=bid_id)
    key = f"bid:{bid_id}"
    _begin_inline(key)
    try:
        return "done", extract_bid_facts(bid_id)
    finally:
        _end_inline(key)


def extract_tender_requirements(tender_id: str) -> int:
    """Runs requirement extraction end-to-end against a fresh DB session —
    shared by the inline path above and the Celery task in workers/tasks.py."""
    from app.db.session import SessionLocal
    from app.models.tender import Tender
    from app.services.extraction.persist import persist_requirements
    from app.services.extraction.tender_requirements import extract_requirements_from_document
    from app.services.llm.client import OllamaClient

    db = SessionLocal()
    try:
        tender = db.get(Tender, uuid.UUID(tender_id))
        if tender is None:
            logger.error("extract_task_tender_missing", tender_id=tender_id)
            return 0

        client = OllamaClient()
        try:
            pages = [(p.page_number, p.text) for p in tender.document.pages]
            grounded = extract_requirements_from_document(client, pages)
        finally:
            client.close()

        return persist_requirements(db, tender, grounded)
    finally:
        db.close()


def extract_bid_facts(bid_id: str) -> int:
    from app.db.session import SessionLocal
    from app.models.vendor import Bid
    from app.services.extraction.persist import persist_facts
    from app.services.extraction.vendor_facts import extract_facts_from_document
    from app.services.llm.client import OllamaClient

    db = SessionLocal()
    try:
        bid = db.get(Bid, uuid.UUID(bid_id))
        if bid is None:
            logger.error("extract_task_bid_missing", bid_id=bid_id)
            return 0

        client = OllamaClient()
        try:
            pages = [(p.page_number, p.text) for p in bid.document.pages]
            grounded = extract_facts_from_document(client, pages)
        finally:
            client.close()

        return persist_facts(db, bid, grounded)
    finally:
        db.close()
