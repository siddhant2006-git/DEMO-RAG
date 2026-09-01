from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_actor, get_db
from app.core.errors import AppError
from app.core.logging import get_logger
from app.models.document import DocumentKind
from app.models.tender import Tender
from app.schemas.document import DocumentOut, DocumentPageOut
from app.schemas.tender import TenderUploadOut
from app.services.audit.trail import record as record_audit
from app.services.ingestion.enqueue import enqueue_ingestion
from app.services.ingestion.upload import save_upload, validate_pdf_upload

router = APIRouter(prefix="/tenders", tags=["tenders"])
logger = get_logger(__name__)


@router.post("", response_model=TenderUploadOut, status_code=201)
async def upload_tender(
    file: UploadFile = File(...),
    title: str = Form(...),
    reference_no: str | None = Form(default=None),
    category: str = Form(default="goods"),
    db: Session = Depends(get_db),
    actor: str = Depends(get_actor),
) -> TenderUploadOut:
    content = await file.read()
    validate_pdf_upload(file.filename or "upload.pdf", file.content_type, len(content))

    saved = save_upload(db, kind=DocumentKind.TENDER, filename=file.filename or "upload.pdf", content=content)

    tender = Tender(title=title, reference_no=reference_no, category=category, document_id=saved.document.id)
    db.add(tender)
    db.commit()
    db.refresh(tender)

    record_audit(
        db,
        actor=actor,
        action="tender.upload",
        entity_type="tender",
        entity_id=str(tender.id),
        after={"title": title, "document_id": str(saved.document.id), "duplicate": saved.duplicate},
    )

    if saved.document.status in ("pending", "failed"):
        enqueue_ingestion(str(saved.document.id))

    db.refresh(saved.document)
    return TenderUploadOut(
        tender_id=tender.id,
        document=DocumentOut.model_validate(saved.document),
        job_id=str(saved.document.id),
        duplicate=saved.duplicate,
    )


@router.get("/{tender_id}")
def get_tender(tender_id: str, db: Session = Depends(get_db)) -> dict:
    import uuid

    tender = db.get(Tender, uuid.UUID(tender_id))
    if tender is None:
        raise AppError("NOT_FOUND", "Tender not found", 404)

    return {
        "id": str(tender.id),
        "title": tender.title,
        "reference_no": tender.reference_no,
        "category": tender.category,
        "document": DocumentOut.model_validate(tender.document),
    }


@router.get("/{tender_id}/pages", response_model=list[DocumentPageOut])
def get_tender_pages(tender_id: str, db: Session = Depends(get_db)) -> list[DocumentPageOut]:
    import uuid

    tender = db.get(Tender, uuid.UUID(tender_id))
    if tender is None:
        raise AppError("NOT_FOUND", "Tender not found", 404)

    return [
        DocumentPageOut(
            page_number=p.page_number,
            char_count=len(p.text.strip()),
            ocr_used=p.ocr_used,
            ocr_confidence=p.ocr_confidence,
            low_confidence=p.low_confidence,
            text_preview=p.text[:200],
        )
        for p in tender.document.pages
    ]


@router.get("/{tender_id}/requirements")
def get_tender_requirements(tender_id: str, db: Session = Depends(get_db)) -> list[dict]:
    import uuid

    tender = db.get(Tender, uuid.UUID(tender_id))
    if tender is None:
        raise AppError("NOT_FOUND", "Tender not found", 404)

    return [
        {
            "id": str(r.id),
            "external_ref": r.external_ref,
            "text": r.text,
            "category": r.category,
            "expected": r.expected,
            "source_page": r.source_page,
            "source_snippet": r.source_snippet,
            "human_reviewed": r.human_reviewed,
        }
        for r in tender.requirements
    ]


@router.get("/{tender_id}/search")
def search_tender(tender_id: str, q: str, db: Session = Depends(get_db)) -> list[dict]:
    """Semantic clause search over the tender document — 'find the clause
    that proves X', for an officer double-checking an extracted requirement
    against the source text."""
    import uuid

    from app.services.retrieval.search import search as run_search

    tender = db.get(Tender, uuid.UUID(tender_id))
    if tender is None:
        raise AppError("NOT_FOUND", "Tender not found", 404)

    results = run_search(str(tender.document_id), q, top_k=5)
    return [
        {"text": r.text, "page_numbers": r.page_numbers, "heading": r.heading, "score": r.score} for r in results
    ]
