#!/usr/bin/env python
"""Seeds a full demo state: uploads the sample tender + bid, ingests both,
seeds the eligibility requirement and claimed fact the demo script depends
on (so the turnover mismatch shows up even without a running Ollama), runs
verification and compliance, and prints the resulting bid id.

Run `python scripts/generate_sample_pdfs.py` first if the sample PDFs don't
exist yet. Pass --use-llm to run real requirement/fact extraction instead of
the seeded values (needs Ollama running).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models.document import DocumentKind  # noqa: E402
from app.models.requirement import Requirement  # noqa: E402
from app.models.tender import Tender  # noqa: E402
from app.models.vendor import Bid, ClaimedFact, Vendor  # noqa: E402
from app.services.compliance.service import run_compliance  # noqa: E402
from app.services.ingestion.pipeline import ingest_document  # noqa: E402
from app.services.ingestion.upload import save_upload  # noqa: E402
from app.services.risk.scorer import score_findings  # noqa: E402
from app.services.verification.cache import verify_with_cache  # noqa: E402

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "data" / "samples"
TENDER_PDF = SAMPLES_DIR / "tenders" / "sample_road_equipment_tender.pdf"
BID_PDF = SAMPLES_DIR / "bids" / "sample_ganga_infra_bid.pdf"

GSTIN = "27AAAPL1234C1Z5"
PAN = "AAAPL1234C"


def _seed_requirement_and_fact(db, tender, bid) -> None:
    """Stands in for LLM extraction so the headline demo scenario (claimed
    6.2 Cr vs. GST-verified 4.1 Cr, against a 5 Cr threshold) works even
    without Ollama running — matches what run_compliance would otherwise
    auto-synthesize from the rule pack, but with the real page/snippet."""
    requirement = Requirement(
        tender_id=tender.id,
        external_ref="REQ-TURNOVER",
        text="Bidder must have average annual turnover >= 5 Cr in last 3 FY.",
        category="turnover",
        expected={"operator": "gte", "value": 50_000_000, "unit": "INR"},
        source_document_id=tender.document_id,
        source_page=2,
        source_snippet="The bidder must have an average annual turnover of at least Rs. 5 Crore",
        human_reviewed=True,
    )
    db.add(requirement)

    fact = ClaimedFact(
        bid_id=bid.id,
        fact_key="financials.avg_annual_turnover",
        raw_value="Rs. 6,20,00,000",
        normalized_value={"value": 62_000_000, "unit": "INR"},
        source_page=2,
        source_snippet="Average annual turnover for the last 3 financial years is Rs. 6,20,00,000.",
    )
    db.add(fact)
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--use-llm", action="store_true", help="Run real LLM extraction instead of seeding")
    args = parser.parse_args()

    if not TENDER_PDF.exists() or not BID_PDF.exists():
        print("Sample PDFs not found — run `python scripts/generate_sample_pdfs.py` first.")
        raise SystemExit(1)

    db = SessionLocal()
    try:
        tender_upload = save_upload(db, kind=DocumentKind.TENDER, filename=TENDER_PDF.name, content=TENDER_PDF.read_bytes())
        tender_doc = ingest_document(db, tender_upload.document)

        tender = Tender(
            title="Tender for Supply of Road Construction Equipment",
            reference_no="TND/2026/0142",
            category="goods",
            document_id=tender_doc.id,
        )
        db.add(tender)
        db.commit()
        db.refresh(tender)

        bid_upload = save_upload(db, kind=DocumentKind.BID, filename=BID_PDF.name, content=BID_PDF.read_bytes())
        bid_doc = ingest_document(db, bid_upload.document)

        vendor = Vendor(name="Ganga Infra Projects Pvt Ltd", gstin=GSTIN, pan=PAN)
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        bid = Bid(vendor_id=vendor.id, tender_id=tender.id, document_id=bid_doc.id)
        db.add(bid)
        db.commit()
        db.refresh(bid)

        if args.use_llm:
            from app.services.extraction.tender_requirements import extract_requirements_from_document
            from app.services.extraction.vendor_facts import extract_facts_from_document
            from app.services.llm.client import OllamaClient

            client = OllamaClient()
            for grounded in extract_requirements_from_document(client, [(p.page_number, p.text) for p in tender_doc.pages]):
                req = grounded.requirement
                db.add(
                    Requirement(
                        tender_id=tender.id,
                        text=req.text,
                        category=req.category,
                        expected={"operator": req.expected_operator, "value": req.expected_value, "unit": req.expected_unit},
                        source_document_id=tender_doc.id,
                        source_page=grounded.page_number,
                        source_snippet=req.source_snippet,
                    )
                )
            for fact in extract_facts_from_document(client, [(p.page_number, p.text) for p in bid_doc.pages]):
                db.add(
                    ClaimedFact(
                        bid_id=bid.id,
                        fact_key=fact.fact_key,
                        raw_value=fact.raw_value,
                        normalized_value=fact.normalized_value,
                        source_page=fact.page_number,
                        source_snippet=fact.source_snippet,
                    )
                )
            db.commit()
        else:
            _seed_requirement_and_fact(db, tender, bid)

        for portal, identifiers in (
            ("GST", {"gstin": GSTIN}),
            ("DEBARMENT", {"gstin": GSTIN, "pan": PAN}),
        ):
            verify_with_cache(db, bid_id=bid.id, portal=portal, identifiers=identifiers)

        results, risk = run_compliance(db, bid)
        assert risk.score == score_findings(results).score  # sanity: run_compliance's own aggregate

        print(f"tender_id: {tender.id}")
        print(f"bid_id: {bid.id}")
        print(f"risk: {risk.score}/100 ({risk.band})")
        for r in results:
            print(f"  {r.rule_id:16s} {r.status:14s} {r.reason}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
