# Architecture

## The golden rule

The LLM **extracts**, it never **decides**. Every PASS/FAIL/NEEDS-REVIEW
verdict comes from `backend/app/services/rules/engine.py` — a pure function
with no LLM calls and no I/O, so the same input always produces the same
output. See `docs/rule_pack_spec.md` for how rules are authored.

## Request-time flow

1. **Ingestion** (`app/services/ingestion/`) — `pdf_loader.py` pulls per-page
   text and word-level bounding boxes via PyMuPDF. Any page with under 50
   characters of embedded text is handed to `ocr.py` (OpenCV deskew/denoise +
   Tesseract), which flags `low_confidence` pages instead of trusting bad OCR
   silently. `layout.py` detects headings and tables so the eligibility
   section can be found and chunked around. Everything lands in `Document` /
   `DocumentPage` rows, keyed by SHA-256 so a re-upload is detected as a
   duplicate rather than re-processed.

2. **Extraction** (`app/services/extraction/`, `app/services/llm/`) — the
   local Ollama model (temperature 0, seed pinned) is prompted per page to
   pull structured requirements (from the tender) or claimed facts (from the
   bid), forced into JSON and validated against a Pydantic schema with a
   repair loop (`llm/json_guard.py`). Every extracted item must carry a
   verbatim source snippet; `extraction/snippet_guard.py` rejects anything
   whose snippet isn't literally present in the page text — the hallucination
   guardrail. `extraction/normalizers.py` and `fact_normalization.py` turn
   messy strings ("Rs. 5,00,00,000", "5 Cr", "5L") into typed values at this
   one boundary, so nothing downstream parses raw strings.

3. **Verification** (`app/services/verification/`) — a `PortalAdapter`
   interface with a mock/live registry switch (`VERIFICATION_MODE`). Mock
   adapters read JSON fixtures from `data/mock_portals/`, so the whole demo
   runs with the network off. Live adapters (GST, Udyam) degrade to
   `status=DOWN` rather than raising when unconfigured or unreachable — never
   a false PASS or FAIL. Results are cached per bid+portal with a TTL
   (`verification/cache.py`).

4. **Rules** (`app/services/rules/`) — `loader.py` parses a YAML rule pack
   with line-number error reporting; `engine.py` resolves each rule's fact
   from `claimed`/`verified` per `source_priority` (government beats
   document — this is where a vendor's inflated claim gets caught against
   the real GST record) and evaluates it with a fixed operator set
   (`operators.py`). `condition.py` parses `applies_if` expressions with a
   tiny grammar, not `eval()`, since rule packs are officer-editable data.

5. **Risk** (`app/services/risk/scorer.py`) — weighted 0-100 score across all
   findings; a FAILed BLOCKER-severity rule forces the `HIGH` band regardless
   of the numeric score.

6. **Compliance** (`app/services/compliance/`) — `service.py` is the glue:
   builds `claimed`/`verified`/`context` from the DB, runs the engine,
   persists `Finding` + `Evidence` rows (an `Evidence` row is required for
   every `Finding` — enforced by always resolving a real page reference, with
   ordered fallbacks from the bid page to the tender page). Re-running
   compliance replaces prior findings rather than accumulating them, since
   the engine is deterministic and the matrix should reflect current facts.

7. **Reports & audit** — `reports/pdf_builder.py` (ReportLab) renders the
   summary, compliance matrix, and an evidence appendix for every non-PASS
   finding, plus both documents' hashes. `audit/trail.py` appends a row for
   every upload, verification run, compliance run, and report download.

## Why ingestion returns instantly

`POST /tenders` and `POST /bids` save the file and return a `job_id`
(the document's own id) immediately; the actual page extraction runs as a
Celery task. If Redis/the worker isn't reachable, the API route catches that
and runs ingestion inline instead — the upload still completes, just
synchronously, so the system degrades rather than breaking when the full
docker-compose stack isn't up.

## Requirement/rule linkage

A `Finding.requirement_id` always points at a real `Requirement` row. When
Phase 2 extraction has already produced one for a rule (matched by
`Requirement.external_ref == rule.id`), that's used — real page and snippet
included. If none exists yet, `compliance/requirement_binding.py`
synthesizes one from the rule pack itself (`text` = the rule's `label`), so
the system produces a usable compliance matrix even before an officer has
reviewed LLM-extracted requirements.
