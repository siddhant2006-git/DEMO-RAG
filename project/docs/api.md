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
- `POST /tenders/{id}/extract` — runs LLM requirement extraction over the
  tender's ingested pages (409 if ingestion hasn't reached `status=done`
  yet). Same enqueue-or-inline pattern as upload: Celery when a worker's up
  (`{job_id, status: "queued", requirements_created: null}`), otherwise runs
  inline (`status: "done"`, with the real count). Extracted requirements are
  matched against the tender's rule pack by category/keyword and get
  `external_ref` set to the matching rule id where a confident match exists;
  unmatched ones keep `external_ref: null` and surface later as a
  `MANUAL_CHECK` finding when compliance runs. Idempotent per (page,
  snippet) — re-running doesn't duplicate rows already extracted from the
  same source line.
- `GET /tenders/{id}/requirements` — every requirement for the tender
  (extracted, officer-synthesized from the rule pack, or manually added),
  including `reviewed_by`/`reviewed_at`.
- `PATCH /tenders/{id}/requirements/{requirement_id}` — officer edit/review.
  Body: any of `text`, `category`, `expected`, `human_reviewed` (all
  optional). Setting `human_reviewed: true` stamps `reviewed_by` (from
  `X-Actor`) and `reviewed_at`; setting it back to `false` clears both.
  Every edit writes a before/after audit log row.

## Bids

- `POST /bids` (multipart) — `file` (PDF), `tender_id`, `vendor_name`,
  `gstin?`, `pan?`, `udyam_number?`, `claims_msme_benefit?`. Reuses an
  existing vendor by GSTIN when one matches. Same duplicate-detection and
  ingestion behavior as tender upload.
- `GET /bids/{id}` — bid detail, vendor, and any extracted claimed facts.
- `GET /bids/{id}/pages` — same shape as the tender pages endpoint.
- `POST /bids/{id}/extract` — runs LLM claimed-fact extraction over the
  bid's ingested pages (409 if ingestion hasn't reached `status=done` yet).
  Same enqueue-or-inline / idempotent-per-(fact_key, page, snippet)
  behavior as the tender-side extract endpoint. Returns
  `{job_id, status, facts_created}`.

## Verification

- `POST /bids/{id}/verification` — looks up the vendor on GST / Udyam /
  debarment (mock or live per `VERIFICATION_MODE`), caches each result for
  `VERIFICATION_CACHE_TTL_SECONDS`, and returns them.
- `GET /bids/{id}/verification` — the cached results, most recent first.

## Compliance

- `POST /bids/{id}/compliance` — runs the deterministic rule engine for the
  bid's tender category, replaces any previous findings for this bid, and
  returns `{risk, findings}`. Each finding carries `expected`, `claimed`,
  `verified`, `status`, `reason`, `severity`, `risk_contribution`, a
  `rule_pack` object (`name`, `version`, `sha256`, `engine_version` — which
  exact rule pack and engine build produced this verdict), and an
  `evidence` object (`document_id`, `page_number`, `bbox`, `snippet`,
  `document_sha256`).
  - A tender requirement not covered by any rule in the pack still gets a
    finding: `rule_id` starts with `MANUAL-`, `status: "NEEDS_REVIEW"`, and
    `weight: 0` (it can never move the risk score) — the UI renders this as
    a "Manual check" chip rather than "Needs review" so it reads as
    "nobody's checked this yet", not "a rule ran and couldn't decide".
  - When a bid states two different values for the same fact across pages,
    `claimed.conflicts` lists every page-cited value and the finding is
    forced to `NEEDS_REVIEW` — the contradiction is the signal, so it's
    never resolved by last-write-wins.
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
