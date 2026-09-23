from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_actor, get_db
from app.core.errors import AppError, parse_uuid
from app.models.finding import Finding
from app.models.vendor import Bid
from app.services.audit.trail import record as record_audit
from app.services.compliance.service import run_compliance
from app.services.risk.scorer import score_findings

router = APIRouter(prefix="/bids", tags=["compliance"])


def _finding_out(f: Finding) -> dict:
    return {
        "rule_id": f.rule_id,
        "requirement_id": str(f.requirement_id),
        "requirement_text": f.requirement.text,
        "expected": f.expected,
        "claimed": f.claimed,
        "verified": f.verified,
        "status": f.status,
        "reason": f.reason,
        "severity": f.severity,
        "risk_contribution": f.risk_contribution,
        "rule_pack": {
            "name": f.rule_pack_name,
            "version": f.rule_pack_version,
            "sha256": f.rule_pack_sha256,
            "engine_version": f.engine_version,
        },
        "evidence": (
            {
                "document_id": str(f.evidence.document_id),
                "page_number": f.evidence.page_number,
                "bbox": f.evidence.bbox,
                "snippet": f.evidence.snippet,
                "document_sha256": f.evidence.document_sha256,
            }
            if f.evidence
            else None
        ),
    }


@router.post("/{bid_id}/compliance")
def run_bid_compliance(bid_id: str, db: Session = Depends(get_db), actor: str = Depends(get_actor)) -> dict:
    bid = db.get(Bid, parse_uuid(bid_id, field="bid_id"))
    if bid is None:
        raise AppError("NOT_FOUND", "Bid not found", 404)

    results, risk = run_compliance(db, bid)

    record_audit(
        db,
        actor=actor,
        action="compliance.run",
        entity_type="bid",
        entity_id=str(bid.id),
        after={"risk_score": risk.score, "band": risk.band, "fail_count": risk.fail_count},
    )

    findings = db.query(Finding).filter(Finding.bid_id == bid.id).all()
    return {
        "risk": {
            "score": risk.score,
            "band": risk.band,
            "forced_by_blocker": risk.forced_by_blocker,
            "pass_count": risk.pass_count,
            "fail_count": risk.fail_count,
            "needs_review_count": risk.needs_review_count,
        },
        "findings": [_finding_out(f) for f in findings],
    }


@router.get("/{bid_id}/compliance")
def get_bid_compliance(bid_id: str, db: Session = Depends(get_db)) -> dict:
    bid = db.get(Bid, parse_uuid(bid_id, field="bid_id"))
    if bid is None:
        raise AppError("NOT_FOUND", "Bid not found", 404)

    findings = db.query(Finding).filter(Finding.bid_id == bid.id).all()
    if not findings:
        raise AppError("NOT_RUN", "Compliance has not been run for this bid yet", 404)

    # Recompute the risk aggregate from persisted findings (weight included)
    # rather than re-running the engine — GET is a cheap read of what the
    # last POST already decided.
    from app.services.rules.engine import FindingResult

    as_results = [
        FindingResult(
            rule_id=f.rule_id,
            label="",
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

    return {
        "risk": {
            "score": risk.score,
            "band": risk.band,
            "forced_by_blocker": risk.forced_by_blocker,
            "pass_count": risk.pass_count,
            "fail_count": risk.fail_count,
            "needs_review_count": risk.needs_review_count,
        },
        "findings": [_finding_out(f) for f in findings],
    }
