#!/usr/bin/env python
"""End-to-end TenderGuard pipeline from the command line, no UI or HTTP needed.

Ingests a tender PDF and a vendor bid PDF, optionally runs LLM-based
requirement/fact extraction (--use-llm, requires Ollama running), verifies
the vendor against government portals (mock by default), runs the
deterministic rule engine, and prints the resulting findings as JSON.

Usage:
  python scripts/run_pipeline_cli.py \
      --tender data/samples/tenders/sample.pdf --tender-title "Supply of X" \
      --bid data/samples/bids/sample_bid.pdf --vendor-name "Acme Pvt Ltd" \
      --gstin 27AAAPL1234C1Z5 [--use-llm]
"""
import argparse
import json
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


def _run_llm_extraction(db, tender, tender_doc, bid, bid_doc) -> None:
    from app.services.extraction.tender_requirements import extract_requirements_from_document
    from app.services.extraction.vendor_facts import extract_facts_from_document
    from app.services.llm.client import OllamaClient

    client = OllamaClient()
    tender_pages = [(p.page_number, p.text) for p in tender_doc.pages]
    bid_pages = [(p.page_number, p.text) for p in bid_doc.pages]

    for grounded in extract_requirements_from_document(client, tender_pages):
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

    for fact in extract_facts_from_document(client, bid_pages):
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tender", required=True, help="Path to the tender PDF")
    parser.add_argument("--tender-title", required=True)
    parser.add_argument("--reference-no", default=None)
    parser.add_argument("--category", default="goods", choices=["goods", "works", "services"])
    parser.add_argument("--bid", required=True, help="Path to the vendor bid PDF")
    parser.add_argument("--vendor-name", required=True)
    parser.add_argument("--gstin", default=None)
    parser.add_argument("--pan", default=None)
    parser.add_argument("--udyam-number", default=None)
    parser.add_argument("--claims-msme", action="store_true")
    parser.add_argument("--use-llm", action="store_true", help="Run LLM requirement/fact extraction (needs Ollama)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        tender_upload = save_upload(
            db, kind=DocumentKind.TENDER, filename=Path(args.tender).name, content=Path(args.tender).read_bytes()
        )
        tender_doc = ingest_document(db, tender_upload.document)

        tender = Tender(
            title=args.tender_title,
            reference_no=args.reference_no,
            category=args.category,
            document_id=tender_doc.id,
        )
        db.add(tender)
        db.commit()
        db.refresh(tender)

        bid_upload = save_upload(
            db, kind=DocumentKind.BID, filename=Path(args.bid).name, content=Path(args.bid).read_bytes()
        )
        bid_doc = ingest_document(db, bid_upload.document)

        vendor = Vendor(name=args.vendor_name, gstin=args.gstin, pan=args.pan, udyam_number=args.udyam_number)
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        bid = Bid(
            vendor_id=vendor.id,
            tender_id=tender.id,
            document_id=bid_doc.id,
            claims_msme_benefit=args.claims_msme,
        )
        db.add(bid)
        db.commit()
        db.refresh(bid)

        if args.use_llm:
            _run_llm_extraction(db, tender, tender_doc, bid, bid_doc)

        results, risk = run_compliance(db, bid)

        output = {
            "tender_id": str(tender.id),
            "bid_id": str(bid.id),
            "risk": {
                "score": risk.score,
                "band": risk.band,
                "forced_by_blocker": risk.forced_by_blocker,
                "pass_count": risk.pass_count,
                "fail_count": risk.fail_count,
                "needs_review_count": risk.needs_review_count,
            },
            "findings": [
                {
                    "rule_id": r.rule_id,
                    "label": r.label,
                    "status": r.status,
                    "severity": r.severity,
                    "reason": r.reason,
                    "expected": r.expected,
                    "claimed": r.claimed,
                    "verified": r.verified,
                    "risk_contribution": r.risk_contribution,
                }
                for r in results
            ],
        }
        print(json.dumps(output, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
