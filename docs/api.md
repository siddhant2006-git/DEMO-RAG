# API reference

Base URL: `http://localhost:8000/api/v1`. Interactive docs (OpenAPI/Swagger)
are always at `http://localhost:8000/docs`. All responses are JSON; errors
use the envelope `{code, message, detail}`.

## Health

- `GET /health` — always returns 200. Reports `dependencies.database` as
  `up` or `down: <reason>` without ever hanging or raising, even if Postgres
  is unreachable.

## Tenders

- `POST /tenders` (multipart) — `file` (PDF), `title`, `reference_no?`,
  `category?` (`goods`/`works`/`services`, default `goods`). Saves the file,
  detects a re-upload by SHA-256, and kicks off ingestion (Celery if a
  worker's up, otherwise runs inline so the demo never depends on Redis).
  Returns `{tender_id, document, job_id, duplicate}`.
- `GET /tenders/{id}` — tender detail + document status.
- `GET /tenders/{id}/pages` — per-page ingestion result: char count, whether
  OCR ran, OCR confidence, and a text preview.

## Bids

- `POST /bids` (multipart) — `file` (PDF), `tender_id`, `vendor_name`,
  `gstin?`, `pan?`, `udyam_number?`, `claims_msme_benefit?`. Reuses an
  existing vendor by GSTIN when one matches. Same duplicate-detection and
  ingestion behavior as tender upload.
- `GET /bids/{id}` — bid detail, vendor, and any extracted claimed facts.
- `GET /bids/{id}/pages` — same shape as the tender pages endpoint.

## Verification

- `POST /bids/{id}/verification` — looks up the vendor on GST / Udyam /
  debarment (mock or live per `VERIFICATION_MODE`), caches each result for
  `VERIFICATION_CACHE_TTL_SECONDS`, and returns them.
- `GET /bids/{id}/verification` — the cached results, most recent first.

## Compliance

- `POST /bids/{id}/compliance` — runs the deterministic rule engine for the
  bid's tender category, replaces any previous findings for this bid, and
  returns `{risk, findings}`. Each finding carries `expected`, `claimed`,
  `verified`, `status`, `reason`, `severity`, `risk_contribution`, and an
  `evidence` object (`document_id`, `page_number`, `bbox`, `snippet`,
  `document_sha256`).
- `GET /bids/{id}/compliance` — re-reads the persisted findings and
  recomputes the risk aggregate from them (no re-run).

## Reports

- `GET /bids/{id}/report` — streams a PDF (`application/pdf`,
  `Content-Disposition: attachment`) built from the last compliance run:
  summary, compliance matrix, and an evidence appendix for every non-PASS
  finding, plus both documents' SHA-256 hashes.

## Audit

Every upload, verification run, compliance run, and report download writes
an append-only row via `app/services/audit/trail.py` (actor from the
`X-Actor` header, default `"officer"`). There's no dedicated `/audit` list
endpoint yet — querying the `audit_logs` table directly is the current path.
