# Demo script (5 minutes)

Rehearse twice. Run at least once with the network disconnected — everything
below works offline with `VERIFICATION_MODE=mock` (the default).

Sample tender/bid PDFs matching this script live in `data/samples/` — run
`python scripts/generate_sample_pdfs.py` to (re)generate them, or
`python scripts/load_sample_data.py` to seed a full demo state.

1. **0:00 — The problem.** Manual bid verification against a tender's
   eligibility criteria takes days per tender, and a missed mismatch between
   what a vendor claims and what's actually on record is expensive.

2. **0:30 — Upload the tender.** `data/samples/tenders/sample_road_equipment_tender.pdf`.
   Point out the extracted eligibility criteria, each traceable to a page in
   the source PDF (`GET /tenders/{id}/pages` / the Requirements screen).

3. **1:30 — Upload the vendor bid.** `data/samples/bids/sample_ganga_infra_bid.pdf`
   for "Ganga Infra Projects Pvt Ltd", GSTIN `27AAAPL1234C1Z5`. Show the
   claimed facts, each with its source snippet — turnover is claimed as
   **Rs. 6,20,00,000**.

4. **2:15 — Run verification.** `POST /bids/{id}/verification` — GST record
   for that GSTIN is fetched (mock data in `data/mock_portals/gst.json`,
   swap `VERIFICATION_MODE=live` for the real thing once portal credentials
   are configured). It shows average annual turnover of **Rs. 4,10,00,000**
   — already a mismatch worth flagging.

5. **3:00 — The moment: the compliance matrix.** `POST /bids/{id}/compliance`.
   REQ-TURNOVER **FAILs**: the tender requires ≥ Rs. 5 Cr, and the rule
   pack's `source_priority: [government, document]` means the GST-verified
   4.1 Cr — not the claimed 6.2 Cr — is what got checked. Everything else
   passes; risk score lands around 30-70 depending on severity mix (a
   BLOCKER fail, like a debarment hit, forces the band straight to HIGH).

6. **3:30 — Click into the FAIL.** Show `claimed` (6.2 Cr, bid.pdf page 2)
   and `verified` (4.1 Cr, GST, cached with a timestamp) side by side —
   that's the fraud signal a plain OCR-to-summary tool never surfaces.

7. **4:15 — Download the report.** `GET /bids/{id}/report` — a filed-ready
   PDF: summary, full compliance matrix, and an evidence appendix quoting
   the exact bid snippet behind the FAIL. Mention the audit trail
   (`audit_logs` table) records every upload, verification, compliance run,
   and report download.

8. **4:45 — Close.** "Every PASS, FAIL, and NEEDS-REVIEW here traces back to
   a page and a government record — not a black-box summary."
