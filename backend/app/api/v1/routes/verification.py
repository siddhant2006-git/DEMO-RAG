import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_actor, get_db
from app.core.errors import AppError
from app.models.vendor import Bid
from app.services.audit.trail import record as record_audit
from app.services.verification.cache import verify_with_cache

router = APIRouter(prefix="/bids", tags=["verification"])


def _result_out(result) -> dict:
    return {
        "portal": result.portal,
        "status": result.status,
        "normalized": result.normalized,
        "fetched_at": result.fetched_at.isoformat(),
    }


@router.post("/{bid_id}/verification")
def run_verification(bid_id: str, db: Session = Depends(get_db), actor: str = Depends(get_actor)) -> dict:
    bid = db.get(Bid, uuid.UUID(bid_id))
    if bid is None:
        raise AppError("NOT_FOUND", "Bid not found", 404)

    lookups: list[tuple[str, dict]] = []
    if bid.vendor.gstin:
        lookups.append(("GST", {"gstin": bid.vendor.gstin}))
        lookups.append(("DEBARMENT", {"gstin": bid.vendor.gstin, "pan": bid.vendor.pan or ""}))
    if bid.vendor.udyam_number:
        lookups.append(("UDYAM", {"udyam_number": bid.vendor.udyam_number}))

    results = [verify_with_cache(db, bid_id=bid.id, portal=portal, identifiers=ids) for portal, ids in lookups]

    record_audit(
        db,
        actor=actor,
        action="verification.run",
        entity_type="bid",
        entity_id=str(bid.id),
        after={"portals": [r.portal for r in results], "statuses": [r.status for r in results]},
    )

    return {"results": [_result_out(r) for r in results]}


@router.get("/{bid_id}/verification")
def get_verification(bid_id: str, db: Session = Depends(get_db)) -> dict:
    from app.models.verification import VerificationResult

    bid = db.get(Bid, uuid.UUID(bid_id))
    if bid is None:
        raise AppError("NOT_FOUND", "Bid not found", 404)

    results = (
        db.query(VerificationResult)
        .filter(VerificationResult.bid_id == bid.id)
        .order_by(VerificationResult.fetched_at.desc())
        .all()
    )
    return {"results": [_result_out(r) for r in results]}
