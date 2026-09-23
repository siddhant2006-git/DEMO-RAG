from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_actor, get_db
from app.core.errors import AppError, parse_uuid
from app.core.logging import get_logger
from app.models.document import DocumentKind
from app.models.requirement import Requirement
from app.models.tender import Tender
from app.schemas.document import DocumentOut, DocumentPageOut
from app.schemas.tender import RequirementUpdate, TenderExtractOut, TenderUploadOut
from app.services.audit.trail import record as record_audit
from app.services.extraction.enqueue import run_or_enqueue_requirement_extraction
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
    tender = db.get(Tender, parse_uuid(tender_id, field="tender_id"))
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
    tender = db.get(Tender, parse_uuid(tender_id, field="tender_id"))
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
    tender = db.get(Tender, parse_uuid(tender_id, field="tender_id"))
    if tender is None:
        raise AppError("NOT_FOUND", "Tender not found", 404)

    return [_requirement_out(r) for r in tender.requirements]


def _requirement_out(r: Requirement) -> dict:
    return {
        "id": str(r.id),
        "external_ref": r.external_ref,
        "text": r.text,
        "category": r.category,
        "expected": r.expected,
        "source_page": r.source_page,
        "source_snippet": r.source_snippet,
        "human_reviewed": r.human_reviewed,
        "reviewed_by": r.reviewed_by,
        "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
    }


@router.post("/{tender_id}/extract", response_model=TenderExtractOut)
def extract_tender_requirements(
    tender_id: str, db: Session = Depends(get_db), actor: str = Depends(get_actor)
) -> TenderExtractOut:
    """Runs LLM requirement extraction over the tender document — the one
    stage that previously only ran from a terminal script. Requires
    ingestion to have completed first (page text is what extraction reads)."""
    tender = db.get(Tender, parse_uuid(tender_id, field="tender_id"))
    if tender is None:
        raise AppError("NOT_FOUND", "Tender not found", 404)
    if tender.document.status != "done":
        raise AppError(
            "NOT_READY", f"Tender document ingestion is '{tender.document.status}', not 'done' yet", 409
        )

    status, created = run_or_enqueue_requirement_extraction(str(tender.id))

    record_audit(
        db,
        actor=actor,
        action="tender.extract",
        entity_type="tender",
        entity_id=str(tender.id),
        after={"status": status, "requirements_created": created},
    )

    return TenderExtractOut(job_id=str(tender.id), status=status, requirements_created=created)


@router.patch("/{tender_id}/requirements/{requirement_id}")
def update_requirement(
    tender_id: str,
    requirement_id: str,
    payload: RequirementUpdate,
    db: Session = Depends(get_db),
    actor: str = Depends(get_actor),
) -> dict:
    """Officer review and edit of an extracted requirement — the human
    checkpoint between LLM extraction and the compliance engine. Every edit
    is recorded with before/after in the audit trail, since a threshold
    misread here silently produces a wrong verdict downstream."""
    tender = db.get(Tender, parse_uuid(tender_id, field="tender_id"))
    if tender is None:
        raise AppError("NOT_FOUND", "Tender not found", 404)

    requirement = db.get(Requirement, parse_uuid(requirement_id, field="requirement_id"))
    if requirement is None or requirement.tender_id != tender.id:
        raise AppError("NOT_FOUND", "Requirement not found for this tender", 404)

    before = _requirement_out(requirement)

    if payload.text is not None:
        requirement.text = payload.text
    if payload.category is not None:
        requirement.category = payload.category
    if payload.expected is not None:
        requirement.expected = payload.expected
    if payload.human_reviewed is not None:
        requirement.human_reviewed = payload.human_reviewed
        if payload.human_reviewed:
            requirement.reviewed_by = actor
            requirement.reviewed_at = datetime.now(timezone.utc)
        else:
            requirement.reviewed_by = None
            requirement.reviewed_at = None

    db.add(requirement)
    db.commit()
    db.refresh(requirement)

    after = _requirement_out(requirement)
    record_audit(
        db,
        actor=actor,
        action="requirement.edit",
        entity_type="requirement",
        entity_id=str(requirement.id),
        before=before,
        after=after,
    )

    return after


@router.get("/{tender_id}/search")
def search_tender(tender_id: str, q: str, db: Session = Depends(get_db)) -> list[dict]:
    """Semantic clause search over the tender document — 'find the clause
    that proves X', for an officer double-checking an extracted requirement
    against the source text."""
    from app.services.retrieval.search import search as run_search

    tender = db.get(Tender, parse_uuid(tender_id, field="tender_id"))
    if tender is None:
        raise AppError("NOT_FOUND", "Tender not found", 404)

    results = run_search(str(tender.document_id), q, top_k=5)
    return [
        {"text": r.text, "page_numbers": r.page_numbers, "heading": r.heading, "score": r.score} for r in results
    ]
