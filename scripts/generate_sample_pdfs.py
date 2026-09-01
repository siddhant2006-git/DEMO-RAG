#!/usr/bin/env python
"""Generates a small synthetic tender + matching vendor bid PDF pair under
data/samples/, for demos and for run_pipeline_cli.py — since we can't ship
real government tender PDFs here, this recreates the shape of one (an
eligibility section with numbered criteria) with content that reproduces the
project's own headline demo scenario: the bid's claimed turnover doesn't
match its GST-verified value.
"""
from pathlib import Path

import pymupdf

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "data" / "samples"


def build_tender_pdf(path: Path) -> None:
    doc = pymupdf.open()

    page = doc.new_page()
    page.insert_text((72, 72), "Tender for Supply of Road Construction Equipment", fontsize=16)
    page.insert_text((72, 100), "Reference No: TND/2026/0142", fontsize=10)
    page.insert_text((72, 118), "Issuing Authority: Public Works Department", fontsize=10)

    page2 = doc.new_page()
    page2.insert_text((72, 60), "3. Eligibility Criteria", fontsize=16)
    lines = [
        "3.1 The bidder must have an average annual turnover of at least Rs. 5 Crore",
        "    in each of the last 3 financial years.",
        "3.2 The bidder must hold a valid and active GST registration.",
        "3.3 The bidder must have a minimum of 5 years of relevant experience in",
        "    similar road construction equipment supply contracts.",
        "3.4 The bidder must not be currently debarred or blacklisted by any",
        "    government department.",
        "3.5 The bidder's PAN must be provided and correctly formatted.",
    ]
    y = 90
    for line in lines:
        page2.insert_text((72, y), line, fontsize=10)
        y += 18

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


def build_bid_pdf(path: Path) -> None:
    doc = pymupdf.open()

    page = doc.new_page()
    page.insert_text((72, 72), "Bid Submission - Ganga Infra Projects Pvt Ltd", fontsize=16)
    page.insert_text((72, 100), "In response to Tender Ref: TND/2026/0142", fontsize=10)

    page2 = doc.new_page()
    page2.insert_text((72, 60), "Company Profile & Financials", fontsize=14)
    lines = [
        "GSTIN: 27AAAPL1234C1Z5",
        "PAN: AAAPL1234C",
        "Average annual turnover for the last 3 financial years is Rs. 6,20,00,000.",
        "The company has 8 years of experience in similar contracts.",
    ]
    y = 90
    for line in lines:
        page2.insert_text((72, y), line, fontsize=10)
        y += 18

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


def main() -> None:
    tender_path = SAMPLES_DIR / "tenders" / "sample_road_equipment_tender.pdf"
    bid_path = SAMPLES_DIR / "bids" / "sample_ganga_infra_bid.pdf"
    build_tender_pdf(tender_path)
    build_bid_pdf(bid_path)
    print(f"Wrote {tender_path}")
    print(f"Wrote {bid_path}")


if __name__ == "__main__":
    main()
