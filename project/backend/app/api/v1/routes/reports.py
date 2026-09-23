from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_actor, get_db
from app.core.errors import AppError, parse_uuid
from app.models.finding import Finding
from app.models.vendor import Bid
from app.services.audit.trail import record as record_audit
from app.services.reports.pdf_builder import EvidenceRef, ReportContext, build_report_pdf
from app.services.rules.engine import FindingResult
from app.services.risk.scorer import score_findings

router = APIRouter(prefix="/bids", tags=["reports"])


@router.get("/{bid_id}/report")
def download_report(bid_id: str, db: Session = Depends(get_db), actor: str = Depends(get_actor)) -> Response:
    bid = db.get(Bid, parse_uuid(bid_id, field="bid_id"))
    if bid is None:
        raise AppError("NOT_FOUND", "Bid not found", 404)

    findings = db.query(Finding).filter(Finding.bid_id == bid.id).all()
    if not findings:
        raise AppError("NOT_RUN", "Compliance has not been run for this bid yet", 404)

    as_results = [
        FindingResult(
            rule_id=f.rule_id,
            label=f.requirement.text,
            severity=f.severity,
            weight=f.weight,
            status=f.status,
            reason=f.reason,
            expected=f.expected,
            claimed=f.claimed,
            verified=f.verified,
            risk_contribution=f.risk_contribution,
        )
        for f in findings
    ]
    risk = score_findings(as_results)

    evidence_by_rule_id = {
        f.rule_id: EvidenceRef(
            document_filename=(
                bid.document.filename if f.evidence.document_id == bid.document_id else bid.tender.document.filename
            ),
            document_sha256=f.evidence.document_sha256,
            page_number=f.evidence.page_number,
            snippet=f.evidence.snippet,
        )
        for f in findings
        if f.evidence
    }

    stamped = findings[0] if findings else None
    ctx = ReportContext(
        tender_title=bid.tender.title,
        tender_reference_no=bid.tender.reference_no,
        vendor_name=bid.vendor.name,
        generated_by=actor,
        findings=as_results,
        risk=risk,
        evidence_by_rule_id=evidence_by_rule_id,
        document_hashes={
            "tender.pdf": bid.tender.document.sha256,
            "bid.pdf": bid.document.sha256,
        },
        rule_pack_name=stamped.rule_pack_name if stamped else None,
        rule_pack_version=stamped.rule_pack_version if stamped else None,
        rule_pack_sha256=stamped.rule_pack_sha256 if stamped else None,
        engine_version=stamped.engine_version if stamped else None,
    )
    pdf_bytes = build_report_pdf(ctx)

    record_audit(
        db,
        actor=actor,
        action="report.download",
        entity_type="bid",
        entity_id=str(bid.id),
        after={"risk_score": risk.score, "band": risk.band},
    )

    filename = f"tenderguard-report-{bid.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
