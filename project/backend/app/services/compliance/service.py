from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.finding import Evidence, Finding
from app.models.requirement import Requirement
from app.models.vendor import Bid
from app.services.compliance.requirement_binding import get_or_create_requirement_for_rule
from app.services.risk.scorer import RiskAssessment, score_findings
from app.services.rules.engine import FactValue, FindingResult, evaluate_rule_pack
from app.services.rules.loader import RulePack, load_rule_pack, resolve_rule_pack_path
from app.services.verification.cache import verify_with_cache

logger = get_logger(__name__)

# Bumped whenever operator/engine semantics change in a way that could shift
# a verdict for the same facts — lets a filed report be told apart from a
# re-run under different engine behavior, alongside the rule pack hash.
ENGINE_VERSION = "1.0.0"


def _build_claimed(bid: Bid) -> dict[str, FactValue]:
    by_key: dict[str, list] = {}
    for fact in bid.claimed_facts:
        if fact.normalized_value.get("value") is None:
            continue
        by_key.setdefault(fact.fact_key, []).append(fact)

    claimed: dict[str, FactValue] = {}
    for fact_key, facts in by_key.items():
        distinct_values = {fact.normalized_value.get("value") for fact in facts}
        # Keep the last-write-wins choice as the primary value for backward
        # compatibility, but when the bid states more than one distinct value
        # for the same fact across pages, that contradiction is itself a
        # signal — surface every page-cited value so the engine forces
        # NEEDS_REVIEW instead of confidently judging whichever came last.
        primary = facts[-1]
        conflicts = (
            [
                {
                    "value": fact.normalized_value.get("value"),
                    "page": fact.source_page,
                    "snippet": fact.source_snippet,
                }
                for fact in facts
            ]
            if len(distinct_values) > 1
            else []
        )
        claimed[fact_key] = FactValue(
            value=primary.normalized_value.get("value"),
            detail={"page": primary.source_page, "snippet": primary.source_snippet},
            conflicts=conflicts,
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
    """Binds each requirement's threshold into the rule-evaluation context.

    Every requirement gets an unambiguous key namespaced by its own
    external_ref (`tender.REQ-TURNOVER.value`) — the intended long-term
    binding, usable once a rule's `threshold_from` is written against it.
    The legacy category-wide key (`tender.turnover_requirement`) is also
    populated for today's rule packs, but only when every requirement in
    that category agrees on the same value: two differently-valued
    requirements colliding on one category (e.g. two "financial" criteria)
    drop the shared key entirely, so `_resolve_expected` reports
    NEEDS_REVIEW instead of silently picking whichever loaded last.
    """
    context: dict = {"bid.claims_msme_benefit": bid.claims_msme_benefit}

    category_values: dict[str, set] = {}
    category_value_by_key: dict[str, object] = {}
    for requirement in bid.tender.requirements:
        expected_value = (requirement.expected or {}).get("value")
        if expected_value is None:
            continue

        if requirement.external_ref:
            context[f"tender.{requirement.external_ref}.value"] = expected_value

        category_key = f"tender.{requirement.category}_requirement"
        category_values.setdefault(category_key, set()).add(expected_value)
        category_value_by_key[category_key] = expected_value

    for category_key, values in category_values.items():
        if len(values) == 1:
            context[category_key] = category_value_by_key[category_key]

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


def _uncovered_requirements(bid: Bid, pack: RulePack) -> list[Requirement]:
    """Requirements extracted from the tender that no rule in this pack
    judges at all — as opposed to a rule that ran and found no matching
    fact. Silently dropping these would look like full coverage when it
    isn't, so each becomes a weight-0 NEEDS_REVIEW finding: visible on the
    matrix, but never able to move the risk score on its own."""
    rule_ids = {rule.id for rule in pack.rules}
    return [
        requirement
        for requirement in bid.tender.requirements
        if requirement.external_ref not in rule_ids
    ]


def _manual_check_result(requirement: Requirement) -> FindingResult:
    return FindingResult(
        rule_id=f"MANUAL-{requirement.id.hex[:8]}",
        label=requirement.text,
        severity="MAJOR",
        weight=0.0,
        status="NEEDS_REVIEW",
        reason="Extracted from the tender but not covered by the rule pack — manual check required.",
        expected=requirement.expected or {},
        claimed=None,
        verified=None,
        risk_contribution=0.0,
    )


def _new_finding(db: Session, bid: Bid, requirement: Requirement, result: FindingResult, pack: RulePack) -> Finding:
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
        rule_pack_name=pack.name,
        rule_pack_version=pack.version,
        rule_pack_sha256=pack.sha256,
        engine_version=ENGINE_VERSION,
    )
    db.add(finding)
    db.flush()
    db.add(Evidence(finding_id=finding.id, **_resolve_evidence_fields(bid, result, requirement)))
    return finding


def run_compliance(db: Session, bid: Bid) -> tuple[list[FindingResult], RiskAssessment]:
    pack = load_rule_pack(resolve_rule_pack_path(bid.tender.category))
    claimed = _build_claimed(bid)
    verified = _build_verified(db, bid)
    context = _build_context(bid)

    rule_results = evaluate_rule_pack(pack, claimed=claimed, verified=verified, context=context)
    uncovered = _uncovered_requirements(bid, pack)
    manual_results = [_manual_check_result(requirement) for requirement in uncovered]
    all_results = rule_results + manual_results
    risk = score_findings(all_results)

    # A re-run should fully reflect current facts, not accumulate stale rows
    # from a previous run — the engine is deterministic, so replace-in-place
    # is safe and keeps the compliance matrix a live view, not a history log.
    db.query(Finding).filter(Finding.bid_id == bid.id).delete()
    db.commit()

    rules_by_id = {r.id: r for r in pack.rules}
    for result in rule_results:
        rule = rules_by_id[result.rule_id]
        requirement = get_or_create_requirement_for_rule(db, bid.tender, rule)
        _new_finding(db, bid, requirement, result, pack)

    for requirement, result in zip(uncovered, manual_results):
        _new_finding(db, bid, requirement, result, pack)

    db.commit()
    return all_results, risk
