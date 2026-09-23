# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

TenderGuard (SIH26100): an officer uploads a tender PDF and a vendor bid PDF; the system extracts
the tender's eligibility requirements and the vendor's claimed facts, verifies those facts against
government portals (GST/Udyam/debarment), runs them through a deterministic YAML rule engine, and
produces a compliance matrix with evidence (page + snippet), a weighted risk score, a PDF report,
and an append-only audit trail.

**The golden rule of this codebase: the LLM extracts, it never decides.** Every PASS/FAIL/NEEDS-REVIEW
verdict comes from `backend/app/services/rules/engine.py` — a pure function, no LLM calls, no I/O, so
the same input always produces the same output. Don't add LLM calls anywhere near the rules/risk/
compliance layers.

See `docs/architecture.md` (full request-time flow), `docs/rule_pack_spec.md` (rule pack YAML format),
`docs/api.md` (endpoint reference), and `docs/demo_script.md` before making non-trivial changes —
they're kept accurate and are more detailed than what's summarized below.

## Commands

All backend commands assume `backend/` as the working directory and its venv (`backend/.venv`) as
the interpreter — `app/config.py`'s `.env` lookup and relative storage paths are anchored to the
project root via `PROJECT_ROOT`, but always activate/use the venv from `backend/`.

```bash
# Backend — run from backend/
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000   # API, http://localhost:8000/docs
.venv/Scripts/python.exe -m pytest -q                                   # full suite
.venv/Scripts/python.exe -m pytest tests/test_rules_engine.py -q        # one file
.venv/Scripts/python.exe -m pytest tests/test_rules_engine.py::test_name -q  # one test
.venv/Scripts/python.exe -m alembic upgrade head                        # apply migrations
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "..."    # new migration after model changes
celery -A app.workers.celery_app worker --loglevel=info --pool=solo     # worker (Windows needs --pool=solo)

# Frontend — run from frontend/
npm run dev      # Vite dev server, http://localhost:5173
npm run build
npm run lint      # oxlint (no test runner configured for the frontend)

# Demo data — run from the project root
python scripts/generate_sample_pdfs.py    # only needed once, creates data/samples/*.pdf
python scripts/load_sample_data.py        # seeds tender+bid+requirement+fact, runs verification+compliance
python scripts/load_sample_data.py --use-llm  # same, but via real Ollama extraction instead of seeded values
python scripts/run_pipeline_cli.py        # end-to-end tender+bid -> JSON findings, no API/UI needed
```

`docker compose up` (repo root) is the intended one-command path (postgres, redis, ollama, api,
worker, frontend, nginx) — see `README.md` "Getting started". **On this machine specifically**,
Docker isn't installed and PostgreSQL's installer is blocked by a network-level 403 on
`get.enterprisedb.com` (confirmed via winget, direct download, and Chocolatey), so the local backend
runs on SQLite (`backend/.env` → `DATABASE_URL=sqlite:///data/tenderguard.db`) and Ollama runs
natively via `ollama serve`. All SQLAlchemy models use the dialect-generic `Uuid`/`JSON` column types
(not `postgresql.UUID`/`JSONB`) specifically so the same code works on both — keep it that way when
adding models/columns. If a real Postgres becomes reachable, only `DATABASE_URL` needs to change.

## Architecture

### Request-time flow

1. **Ingestion** (`services/ingestion/`) — `pdf_loader.py` (PyMuPDF) pulls per-page text + word-level
   bboxes; any page under ~50 chars of embedded text falls back to `ocr.py` (OpenCV deskew/denoise +
   Tesseract), which flags `low_confidence` rather than trusting bad OCR silently. Documents are keyed
   by SHA-256 so a re-upload is detected as a duplicate. `POST /tenders` and `POST /bids` return
   immediately (`services/ingestion/enqueue.py` probes whether Redis is actually reachable and runs
   ingestion inline if not — the upload always completes, sync or async).

2. **Extraction** (`services/extraction/`, `services/llm/`) — Ollama (temp 0, seed pinned) is prompted
   per page to pull structured requirements or claimed facts, forced into JSON and schema-validated
   with a repair loop (`llm/json_guard.py`). `extraction/snippet_guard.py` rejects any extraction whose
   source snippet isn't literally present in the page text — this is the hallucination guardrail, not
   optional. `normalizers.py`/`fact_normalization.py` is the one place messy strings ("Rs. 5,00,00,000",
   "5 Cr") become typed values; nothing downstream should parse raw strings.

3. **Verification** (`services/verification/`) — `PortalAdapter` interface, `registry.py` switches
   between mock (`data/mock_portals/*.json`) and live adapters per `VERIFICATION_MODE`. Live adapters
   degrade to `status=DOWN` rather than raising — never a false PASS/FAIL. Results cached per
   bid+portal with a TTL (`verification/cache.py`) — note the cache's timestamp comparison normalizes
   naive-vs-aware datetimes since SQLite (unlike Postgres) doesn't preserve tzinfo on `DateTime(timezone=True)`.

4. **Rules** (`services/rules/`) — `loader.py` parses a rule pack YAML (`backend/rules/*.yaml`) with
   line-tracking errors; `engine.py` resolves each rule's `fact` from `claimed`/`verified` per
   `source_priority` (listing `government` first is how a vendor's inflated claim gets caught against
   the real GST record) and evaluates it via a fixed operator set (`operators.py`). `condition.py`
   parses `applies_if` with a tiny grammar — never `eval()` — since rule packs are officer-editable data.

5. **Risk** (`services/risk/scorer.py`) — weighted 0-100 score; a FAILed `BLOCKER`-severity rule forces
   the `HIGH` band regardless of the numeric score.

6. **Compliance** (`services/compliance/service.py`) — glues 1-5 together: builds `claimed`/`verified`/
   `context` from the DB, runs the engine, replaces (not appends) this bid's `Finding` rows, and writes
   one `Evidence` row per `Finding` (DB-adjacent invariant: a finding is never persisted without a real
   page reference — `_resolve_evidence_fields` falls back bid page → tender page → page 1).

7. **Reports/audit** — `reports/pdf_builder.py` (ReportLab) renders summary + matrix + evidence
   appendix + document hashes. `audit/trail.py` appends a row for every upload/verification/compliance
   run/report download (actor from the `X-Actor` header, default `"officer"` — there's no real auth).

### Data model

`Tender 1:N Requirement`, `Vendor 1:N Bid 1:N ClaimedFact`, `Bid 1:N VerificationResult`,
`Bid 1:N Finding 1:1 Evidence`, append-only `AuditLog`. A `Finding.requirement_id` always points at a
real `Requirement` — either one extraction already produced (matched by `external_ref == rule.id`) or
one synthesized on the fly from the rule pack (`compliance/requirement_binding.py`) so the compliance
matrix works even before an officer has reviewed extracted requirements. See `docs/rule_pack_spec.md`
for the rule YAML field reference (`id`, `severity`, `weight`, `fact`, `operator`, `value`/
`threshold_from`, `source_priority`, `applies_if`).

### Frontend

React Router pages under `src/pages/` (`Upload` → `Requirements` → `ComplianceMatrix` →
`EvidenceViewer` → `Reports`) share IDs (tender/bid) via `SessionContext` (`src/store/`), which
persists to `localStorage` under the key `tenderguard.session`. `src/api/client.js` is a thin axios
wrapper around the `/api/v1` endpoints in `docs/api.md`.

### Cross-cutting conventions

- Errors: raise `app.core.errors.AppError(code, message, status_code, detail)`; the global handler
  (`core/errors.py`) turns it (and validation/HTTP/unhandled exceptions) into the `{code, message,
  detail}` envelope every endpoint returns.
- Settings: `app/config.py`'s `Settings` reads `backend/.env` regardless of process cwd; relative
  `upload_dir`/`vectorstore_dir`/`mock_portal_dir`/sqlite-DB paths resolve against `PROJECT_ROOT`
  (the project root, one level above `backend/`) via `resolved_database_url` and a field validator —
  not against whatever directory a script happens to be launched from. Docker's `api`/`worker`
  services override these three dirs directly in `docker-compose.yml` since its mount layout differs
  (`./data` → `/app/data`, nested under the backend mount rather than a sibling of it).
