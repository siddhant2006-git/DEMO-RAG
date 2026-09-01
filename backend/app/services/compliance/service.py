from pathlib import Path

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.finding import Evidence, Finding
from app.models.vendor import Bid
from app.services.compliance.requirement_binding import get_or_create_requirement_for_rule
from app.services.risk.scorer import RiskAssessment, score_findings
from app.services.rules.engine import FactValue, FindingResult, evaluate_rule_pack
from app.services.rules.loader import load_rule_pack
from app.services.verification.cache import verify_with_cache

logger = get_logger(__name__)

RULES_DIR = Path(__file__).resolve().parents[3] / "rules"


def _rule_pack_path(category: str) -> Path:
    path = RULES_DIR / f"default_{category}.yaml"
    return path if path.exists() else RULES_DIR / "default_goods.yaml"


def _build_claimed(bid: Bid) -> dict[str, FactValue]:
    claimed: dict[str, FactValue] = {}
    for fact in bid.claimed_facts:
        value = fact.normalized_value.get("value")
        if value is None:
            continue
        # last-write-wins on duplicate fact_key across pages — fine for the
        # current scope; an officer-facing conflict view is a later phase.
        claimed[fact.fact_key] = FactValue(
            value=value,
            detail={"page": fact.source_page, "snippet": fact.source_snippet},
        )
    return claimed


def _build_verified(db: Session, bid: Bid) -> dict[str, FactValue]:
    verified: dict[str, FactValue] = {}
    lookups: list[tuple[str, dict]] = []

    if bid.vendor.gstin:
        lookups.append(("GST", {"gstin": bid.vendor.gstin}))
        lookups.append(("DEBARMENT", {"gstin": bid.vendor.gstin, "pan": bid.vendor.pan or ""}))
    if bid.vendor.udyam_number:
        lookups.append(("UDYAM", {"udyam_number": bid.vendor.udyam_number}))

    for portal, identifiers in lookups:
        result = verify_with_cache(db, bid_id=bid.id, portal=portal, identifiers=identifiers)
        if result.status != "UP":
            logger.info("verification_unavailable", portal=portal, status=result.status, bid_id=str(bid.id))
            continue
        for fact_key, value in result.normalized.items():
            verified[fact_key] = FactValue(
                value=value, detail={"portal": result.portal, "fetched_at": result.fetched_at.isoformat()}
            )
    return verified


def _build_context(bid: Bid) -> dict:
    context: dict = {"bid.claims_msme_benefit": bid.claims_msme_benefit}
    for requirement in bid.tender.requirements:
        expected_value = (requirement.expected or {}).get("value")
        if expected_value is not None:
            context[f"tender.{requirement.category}_requirement"] = expected_value
    return context


def _resolve_evidence_fields(bid: Bid, result: FindingResult, requirement) -> dict:
    """Every finding must get an evidence row — this picks the most specific
    real source available: the bid page the fact was claimed on, then the
    tender page the requirement came from, then a same-document fallback so
    the DB's not-null constraint never blocks a save."""
    claimed_source = (result.claimed or {}).get("source") or {}
    if claimed_source.get("page"):
        return {
            "document_id": bid.document_id,
            "document_sha256": bid.document.sha256,
            "page_number": claimed_source["page"],
            "snippet": claimed_source.get("snippet") or "(claimed value; no snippet recorded)",
            "bbox": claimed_source.get("bbox"),
        }
    if requirement.source_page:
        return {
            "document_id": requirement.source_document_id or bid.tender.document_id,
            "document_sha256": bid.tender.document.sha256,
            "page_number": requirement.source_page,
            "snippet": requirement.source_snippet or requirement.text,
            "bbox": None,
        }
    return {
        "document_id": bid.tender.document_id,
        "document_sha256": bid.tender.document.sha256,
        "page_number": 1,
        "snippet": requirement.text,
        "bbox": None,
    }


def run_compliance(db: Session, bid: Bid) -> tuple[list[FindingResult], RiskAssessment]:
    pack = load_rule_pack(_rule_pack_path(bid.tender.category))
    claimed = _build_claimed(bid)
    verified = _build_verified(db, bid)
    context = _build_context(bid)

    results = evaluate_rule_pack(pack, claimed=claimed, verified=verified, context=context)
    risk = score_findings(results)

    # A re-run should fully reflect current facts, not accumulate stale rows
    # from a previous run — the engine is deterministic, so replace-in-place
    # is safe and keeps the compliance matrix a live view, not a history log.
    db.query(Finding).filter(Finding.bid_id == bid.id).delete()
    db.commit()

    rules_by_id = {r.id: r for r in pack.rules}
    for result in results:
        rule = rules_by_id[result.rule_id]
        requirement = get_or_create_requirement_for_rule(db, bid.tender, rule)

        finding = Finding(
            bid_id=bid.id,
            requirement_id=requirement.id,
            rule_id=result.rule_id,
            weight=result.weight,
            expected=result.expected,
            claimed=result.claimed or {},
            verified=result.verified or {},
            status=result.status,
            reason=result.reason,
            severity=result.severity,
            risk_contribution=result.risk_contribution,
        )
        db.add(finding)
        db.flush()

        db.add(Evidence(finding_id=finding.id, **_resolve_evidence_fields(bid, result, requirement)))

    db.commit()
    return results, risk
