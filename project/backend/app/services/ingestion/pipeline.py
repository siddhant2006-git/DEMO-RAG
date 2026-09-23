from dataclasses import asdict

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.document import Document, DocumentPage
from app.services.ingestion.layout import detect_headings
from app.services.ingestion.ocr import ocr_page
from app.services.ingestion.pdf_loader import extract_pdf
from app.services.retrieval.chunker import chunk_document
from app.services.retrieval.vector_store import build_index

logger = get_logger(__name__)


def ingest_document(db: Session, document: Document) -> Document:
    """Extract every page of `document`, OCR the ones with a sparse text layer,
    and persist DocumentPage rows. Never lets an OCR failure crash the whole
    job — a page whose OCR errors out is marked low_confidence instead, so a
    bad scan surfaces for officer review rather than silently failing.
    """
    document.status = "processing"
    db.add(document)
    db.commit()

    try:
        extraction = extract_pdf(document.storage_path)
        document.page_count = extraction.page_count

        for page in extraction.pages:
            if page.needs_ocr:
                try:
                    ocr_result = ocr_page(document.storage_path, page.page_number)
                    text = ocr_result.text
                    layout = [asdict(w) for w in ocr_result.layout]
                    ocr_confidence = ocr_result.confidence
                    low_confidence = ocr_result.low_confidence
                except Exception:
                    logger.error(
                        "ocr_failed", document_id=str(document.id), page_number=page.page_number, exc_info=True
                    )
                    text = page.text
                    layout = [asdict(w) for w in page.layout]
                    ocr_confidence = 0.0
                    low_confidence = True
                ocr_used = True
            else:
                text = page.text
                layout = [asdict(w) for w in page.layout]
                ocr_used = False
                ocr_confidence = None
                low_confidence = False

            db.add(
                DocumentPage(
                    document_id=document.id,
                    page_number=page.page_number,
                    text=text,
                    ocr_used=ocr_used,
                    ocr_confidence=ocr_confidence,
                    low_confidence=low_confidence,
                    layout=layout,
                )
            )

        document.status = "done"
    except Exception:
        logger.error("ingestion_failed", document_id=str(document.id), exc_info=True)
        document.status = "failed"

    db.add(document)
    db.commit()
    db.refresh(document)

    if document.status == "done":
        try:
            pages = [(p.page_number, p.text) for p in extraction.pages]
            headings = detect_headings(document.storage_path)
            build_index(str(document.id), chunk_document(pages, headings))
        except Exception:
            # Retrieval indexing is an enhancement, not core to ingestion —
            # a failure here must never mark an otherwise-successful ingest as failed.
            logger.error("vector_index_build_failed", document_id=str(document.id), exc_info=True)

    return document
