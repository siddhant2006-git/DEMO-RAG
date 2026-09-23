from sqlalchemy.orm import Session

from app.models.requirement import Requirement
from app.models.tender import Tender
from app.models.vendor import Bid, ClaimedFact
from app.services.compliance.requirement_binding import match_rule_for_extracted
from app.services.extraction.tender_requirements import GroundedRequirement
from app.services.extraction.vendor_facts import GroundedFact
from app.services.rules.loader import load_rule_pack, resolve_rule_pack_path


def persist_requirements(db: Session, tender: Tender, grounded: list[GroundedRequirement]) -> int:
    """Writes extracted requirements, setting external_ref to the matching
    rule id where one exists so requirement_binding.py's
    get_or_create_requirement_for_rule finds this real, page-sourced
    requirement instead of synthesizing one from the rule pack. A
    requirement with no confident match keeps external_ref=None and is
    picked up by the compliance engine's uncovered-requirement bucket.

    Re-running extraction is idempotent per (page, snippet): a requirement
    already recorded from that exact source line is skipped rather than
    duplicated.
    """
    pack = load_rule_pack(resolve_rule_pack_path(tender.category))
    used_refs = {r.external_ref for r in tender.requirements if r.external_ref}
    existing_sources = {(r.source_page, r.source_snippet) for r in tender.requirements}

    created = 0
    for item in grounded:
        req = item.requirement
        if (item.page_number, req.source_snippet) in existing_sources:
            continue

        expected = {}
        if req.expected_operator is not None:
            expected = {"operator": req.expected_operator, "value": req.expected_value, "unit": req.expected_unit}

        rule = match_rule_for_extracted(pack, category=req.category, text=req.text, used_refs=used_refs)
        external_ref = None
        if rule is not None:
            external_ref = rule.id
            used_refs.add(rule.id)

        db.add(
            Requirement(
                tender_id=tender.id,
                external_ref=external_ref,
                text=req.text,
                category=req.category,
                expected=expected,
                source_document_id=tender.document_id,
                source_page=item.page_number,
                source_snippet=req.source_snippet,
                human_reviewed=False,
            )
        )
        existing_sources.add((item.page_number, req.source_snippet))
        created += 1

    db.commit()
    return created


def persist_facts(db: Session, bid: Bid, grounded: list[GroundedFact]) -> int:
    """Writes extracted claimed facts. Idempotent per (fact_key, page,
    snippet) so re-running extraction on a bid doesn't duplicate facts the
    compliance engine would then have to reconcile as conflicts."""
    existing_sources = {(f.fact_key, f.source_page, f.source_snippet) for f in bid.claimed_facts}

    created = 0
    for item in grounded:
        key = (item.fact_key, item.page_number, item.source_snippet)
        if key in existing_sources:
            continue

        db.add(
            ClaimedFact(
                bid_id=bid.id,
                fact_key=item.fact_key,
                raw_value=item.raw_value,
                normalized_value=item.normalized_value,
                source_page=item.page_number,
                source_snippet=item.source_snippet,
            )
        )
        existing_sources.add(key)
        created += 1

    db.commit()
    return created
