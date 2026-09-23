import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401 - registers all tables on Base.metadata
from app.db.base import Base
from app.models.document import Document, DocumentKind
from app.models.requirement import Requirement
from app.models.tender import Tender
from app.models.vendor import Bid, ClaimedFact, Vendor
from app.services.compliance.service import run_compliance

RULES_DIR = "rules"


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _make_document(db, *, sha256: str) -> Document:
    doc = Document(kind=DocumentKind.TENDER, filename="x.pdf", storage_path="x.pdf", sha256=sha256, status="done")
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _make_bid_with_tender(db, *, requirements: list[Requirement]) -> Bid:
    tender_doc = _make_document(db, sha256="tender-sha")
    tender = Tender(title="T", category="goods", document_id=tender_doc.id)
    db.add(tender)
    db.commit()
    db.refresh(tender)

    for req in requirements:
        req.tender_id = tender.id
        db.add(req)
    db.commit()

    bid_doc = _make_document(db, sha256="bid-sha")
    vendor = Vendor(name="V")
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    bid = Bid(vendor_id=vendor.id, tender_id=tender.id, document_id=bid_doc.id)
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid


def test_uncovered_requirement_becomes_weight_zero_manual_check(db_session):
    """A3 layer 1: a tender requirement with no matching rule in the pack
    must still show up on the matrix — as a NEEDS_REVIEW row that can't move
    the risk score — rather than silently vanishing."""
    manual_req = Requirement(
        external_ref=None,
        text="ISO 9001:2015 certification required",
        category="certification",
        expected={},
        source_page=4,
        source_snippet="ISO 9001:2015 certification required",
    )
    bid = _make_bid_with_tender(db_session, requirements=[manual_req])

    results, risk = run_compliance(db_session, bid)

    manual_results = [r for r in results if r.rule_id.startswith("MANUAL-")]
    assert len(manual_results) == 1
    assert manual_results[0].status == "NEEDS_REVIEW"
    assert manual_results[0].weight == 0.0
    assert manual_results[0].risk_contribution == 0.0
    # weight-0 findings must never move the score, however many exist
    assert risk.score == pytest.approx(score_only_rule_findings(results))


def score_only_rule_findings(results):
    from app.services.risk.scorer import score_findings

    rule_only = [r for r in results if not r.rule_id.startswith("MANUAL-")]
    return score_findings(rule_only).score


def test_findings_are_stamped_with_rule_pack_and_engine_version(db_session):
    """A4: every finding must record which rule pack (name/version/hash) and
    engine build produced it, so a report stays re-derivable later."""
    bid = _make_bid_with_tender(db_session, requirements=[])
    run_compliance(db_session, bid)

    from app.models.finding import Finding

    findings = db_session.query(Finding).filter(Finding.bid_id == bid.id).all()
    assert findings
    for f in findings:
        assert f.rule_pack_name == "Default Goods Procurement Pack"
        assert f.rule_pack_version == 1
        assert f.rule_pack_sha256 and len(f.rule_pack_sha256) == 64
        assert f.engine_version


def test_conflicting_claim_forces_needs_review(db_session):
    """B2: a bid claiming two different turnover figures on two different
    pages must not be silently resolved by last-write-wins — it's a
    contradiction, and the engine must flag it rather than pick one."""
    turnover_req = Requirement(
        external_ref="REQ-TURNOVER",
        text="Bidder must have average annual turnover >= 5 Cr in last 3 FY.",
        category="turnover",
        expected={"operator": "gte", "value": 50_000_000, "unit": "INR"},
        source_page=2,
        source_snippet="turnover >= 5 Cr",
    )
    bid = _make_bid_with_tender(db_session, requirements=[turnover_req])

    db_session.add_all(
        [
            ClaimedFact(
                bid_id=bid.id,
                fact_key="financials.avg_annual_turnover",
                raw_value="Rs. 6,20,00,000",
                normalized_value={"value": 62_000_000, "unit": "INR"},
                source_page=4,
                source_snippet="Average annual turnover is Rs. 6,20,00,000.",
            ),
            ClaimedFact(
                bid_id=bid.id,
                fact_key="financials.avg_annual_turnover",
                raw_value="Rs. 4,10,00,000",
                normalized_value={"value": 41_000_000, "unit": "INR"},
                source_page=17,
                source_snippet="Average annual turnover is Rs. 4,10,00,000.",
            ),
        ]
    )
    db_session.commit()

    results, _ = run_compliance(db_session, bid)
    turnover = next(r for r in results if r.rule_id == "REQ-TURNOVER")

    assert turnover.status == "NEEDS_REVIEW"
    assert "different values" in turnover.reason
    assert "conflicts" in (turnover.claimed or {})


def test_two_requirements_same_category_different_values_drop_shared_key(db_session):
    """B3: two requirements of the same category with different thresholds
    must not silently pick one — the shared category-wide context key is
    dropped so an ambiguous rule reports NEEDS_REVIEW instead of a coin flip,
    while each requirement's own external_ref-keyed threshold still binds
    correctly."""
    from app.services.compliance.service import _build_context

    req_a = Requirement(
        external_ref="REQ-A",
        text="Requirement A",
        category="financial",
        expected={"operator": "gte", "value": 100},
    )
    req_b = Requirement(
        external_ref="REQ-B",
        text="Requirement B",
        category="financial",
        expected={"operator": "gte", "value": 200},
    )
    bid = _make_bid_with_tender(db_session, requirements=[req_a, req_b])

    context = _build_context(bid)
    assert context["tender.REQ-A.value"] == 100
    assert context["tender.REQ-B.value"] == 200
    assert "tender.financial_requirement" not in context
