from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_actor, get_db
from app.core.errors import AppError, parse_uuid
from app.core.logging import get_logger
from app.models.document import DocumentKind
from app.models.tender import Tender
from app.models.vendor import Bid, Vendor
from app.schemas.document import DocumentOut, DocumentPageOut
from app.schemas.vendor import BidExtractOut, BidUploadOut
from app.services.audit.trail import record as record_audit
from app.services.extraction.enqueue import run_or_enqueue_fact_extraction
from app.services.ingestion.enqueue import enqueue_ingestion
from app.services.ingestion.upload import save_upload, validate_pdf_upload

router = APIRouter(prefix="/bids", tags=["bids"])
logger = get_logger(__name__)


def _get_or_create_vendor(db: Session, *, name: str, gstin: str | None, pan: str | None, udyam_number: str | None) -> Vendor:
    if gstin:
        # gstin has no DB-level uniqueness constraint, so more than one vendor
        # row can legitimately exist for it (e.g. seed scripts re-run) — take
        # the most recently created rather than crashing on a scalar lookup.
        existing = (
            db.execute(select(Vendor).where(Vendor.gstin == gstin).order_by(Vendor.created_at.desc()))
            .scalars()
            .first()
        )
        if existing is not None:
            return existing

    vendor = Vendor(name=name, gstin=gstin, pan=pan, udyam_number=udyam_number)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.post("", response_model=BidUploadOut, status_code=201)
async def upload_bid(
    file: UploadFile = File(...),
    tender_id: str = Form(...),
    vendor_name: str = Form(...),
    gstin: str | None = Form(default=None),
    pan: str | None = Form(default=None),
    udyam_number: str | None = Form(default=None),
    claims_msme_benefit: bool = Form(default=False),
    db: Session = Depends(get_db),
    actor: str = Depends(get_actor),
) -> BidUploadOut:
    tender = db.get(Tender, parse_uuid(tender_id, field="tender_id"))
    if tender is None:
        raise AppError("NOT_FOUND", "Tender not found", 404)

    content = await file.read()
    validate_pdf_upload(file.filename or "bid.pdf", file.content_type, len(content))

    saved = save_upload(db, kind=DocumentKind.BID, filename=file.filename or "bid.pdf", content=content)
    vendor = _get_or_create_vendor(db, name=vendor_name, gstin=gstin, pan=pan, udyam_number=udyam_number)

    bid = Bid(
        vendor_id=vendor.id,
        tender_id=tender.id,
        document_id=saved.document.id,
        claims_msme_benefit=claims_msme_benefit,
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)

    record_audit(
        db,
        actor=actor,
        action="bid.upload",
        entity_type="bid",
        entity_id=str(bid.id),
        after={"tender_id": str(tender.id), "vendor_id": str(vendor.id), "duplicate": saved.duplicate},
    )

    if saved.document.status in ("pending", "failed"):
        enqueue_ingestion(str(saved.document.id))

    db.refresh(saved.document)
    return BidUploadOut(
        bid_id=bid.id,
        vendor_id=vendor.id,
        document=DocumentOut.model_validate(saved.document),
        job_id=str(saved.document.id),
        duplicate=saved.duplicate,
    )


@router.get("/{bid_id}")
def get_bid(bid_id: str, db: Session = Depends(get_db)) -> dict:
    bid = db.get(Bid, parse_uuid(bid_id, field="bid_id"))
    if bid is None:
        raise AppError("NOT_FOUND", "Bid not found", 404)

    return {
        "id": str(bid.id),
        "tender_id": str(bid.tender_id),
        "vendor": {
            "id": str(bid.vendor.id),
            "name": bid.vendor.name,
            "gstin": bid.vendor.gstin,
            "pan": bid.vendor.pan,
            "udyam_number": bid.vendor.udyam_number,
        },
        "claims_msme_benefit": bid.claims_msme_benefit,
        "document": DocumentOut.model_validate(bid.document),
        "claimed_facts": [
            {
                "fact_key": f.fact_key,
                "raw_value": f.raw_value,
                "normalized_value": f.normalized_value,
                "source_page": f.source_page,
                "source_snippet": f.source_snippet,
            }
            for f in bid.claimed_facts
        ],
    }


@router.post("/{bid_id}/extract", response_model=BidExtractOut)
def extract_bid_facts(bid_id: str, db: Session = Depends(get_db), actor: str = Depends(get_actor)) -> BidExtractOut:
    """Runs LLM claimed-fact extraction over the bid document — the same
    stage the tender side gets via POST /tenders/{id}/extract, previously
    reachable only from scripts/load_sample_data.py --use-llm."""
    bid = db.get(Bid, parse_uuid(bid_id, field="bid_id"))
    if bid is None:
        raise AppError("NOT_FOUND", "Bid not found", 404)
    if bid.document.status != "done":
        raise AppError("NOT_READY", f"Bid document ingestion is '{bid.document.status}', not 'done' yet", 409)

    status, created = run_or_enqueue_fact_extraction(str(bid.id))

    record_audit(
        db,
        actor=actor,
        action="bid.extract",
        entity_type="bid",
        entity_id=str(bid.id),
        after={"status": status, "facts_created": created},
    )

    return BidExtractOut(job_id=str(bid.id), status=status, facts_created=created)


@router.get("/{bid_id}/pages", response_model=list[DocumentPageOut])
def get_bid_pages(bid_id: str, db: Session = Depends(get_db)) -> list[DocumentPageOut]:
    bid = db.get(Bid, parse_uuid(bid_id, field="bid_id"))
    if bid is None:
        raise AppError("NOT_FOUND", "Bid not found", 404)

    return [
        DocumentPageOut(
            page_number=p.page_number,
            char_count=len(p.text.strip()),
            ocr_used=p.ocr_used,
            ocr_confidence=p.ocr_confidence,
            low_confidence=p.low_confidence,
            text_preview=p.text[:200],
        )
        for p in bid.document.pages
    ]
