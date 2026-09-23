# TenderGuard — Solution Definition

**Problem ID:** SIH26100 (Smart India Hackathon) — AI Tender & Vendor Compliance Verification
**Companion documents:** `problem.md` (the problem) · `readme0111.md` (architecture) · `project01.md` (blueprint) · `docs/`
**Status of the codebase at the time of writing:** backend suite green — **95 tests passing** (`backend/.venv/Scripts/python.exe -m pytest -q`)

This document is the point-by-point answer to `problem.md`. Every claim below names the file that
implements it, so any statement here can be checked against the code in one hop.

---

## 1. The solution in one sentence

> TenderGuard splits the officer's job into two halves that must never mix: an **LLM reads** the
> tender and the bid into structured, page-cited facts, and a **pure-function rule engine decides**
> — resolving every fact from the government record first, attaching a page and a snippet to every
> verdict, and degrading to "a human must look at this" wherever it is not certain.

---

## 2. The one design decision everything else follows from

> **The golden rule: the LLM extracts. It never decides.**

`backend/app/services/rules/engine.py` is a pure function — no LLM call, no database, no clock, no
network. Feed it the same rule pack, the same facts and the same context and it returns the same
findings, forever. That single constraint is what converts an unciteable chatbot answer into a
procurement record that survives a challenge.

| Layer | File | LLM? | Deterministic? |
|---|---|---|---|
| Ingestion (PDF → page text + boxes) | `services/ingestion/` | No | Yes |
| Extraction (text → typed facts) | `services/extraction/` | **Yes** | No — guarded four ways |
| Normalization (strings → values) | `services/extraction/normalizers.py` | No | Yes |
| Verification (government portals) | `services/verification/` | No | Yes, cached |
| **Rule engine (the verdict)** | `services/rules/engine.py` | **Never** | **Yes** |
| Risk scoring | `services/risk/scorer.py` | Never | Yes |
| Evidence · audit · report | `services/compliance/`, `services/audit/`, `services/reports/` | No | Yes |

The LLM sits in exactly one band of that table, and everything it emits is checked against the
literal page text before it is allowed to leave that band (§4, P6).

---

## 3. End-to-end: what actually happens

```
POST /api/v1/tenders            upload tender PDF   → Document(sha256, kind=TENDER) → ingest
POST /api/v1/tenders/{id}/extract                   → Requirement rows (page + snippet each)
POST /api/v1/bids               upload bid PDF      → Vendor + Bid + Document(kind=BID) → ingest
POST /api/v1/bids/{id}/extract                      → ClaimedFact rows (normalized + page-cited)
POST /api/v1/bids/{id}/verification                 → VerificationResult per portal (cached, TTL)
POST /api/v1/bids/{id}/compliance                   → Finding + Evidence per rule, + risk score
GET  /api/v1/bids/{id}/report                       → PDF stamped with document + rule-pack hashes
GET  /api/v1/audit?entity_id=…                      → append-only history of all of the above
```

Each stage in detail:

1. **Upload** (`services/ingestion/upload.py`) — extension/content-type check, size ceiling
   (`MAX_UPLOAD_MB`, default 50), zero-byte rejection, then SHA-256 of the bytes. A document whose
   hash is already stored *for the same kind* reuses the existing row instead of re-storing and
   re-ingesting it, and the response says `duplicate: true`.
2. **Ingestion** (`services/ingestion/pipeline.py`) — PyMuPDF extracts per-page text plus word-level
   bounding boxes; any page under 50 characters of embedded text is handed to the OCR fallback;
   results land as `DocumentPage` rows carrying `ocr_used`, `ocr_confidence`, `low_confidence` and
   `layout`. Vector indexing runs afterwards and is explicitly allowed to fail without failing the
   ingest.
3. **Extraction** (`services/extraction/`) — one Ollama call per page at temperature 0, forced JSON,
   validated against a Pydantic schema, and every returned snippet checked for literal presence on
   that page. Survivors are normalized to typed values and persisted idempotently per
   `(fact_key, page, snippet)`.
4. **Verification** (`services/verification/`) — an adapter per portal behind a registry; results
   cached per `(bid, portal)` for `VERIFICATION_CACHE_TTL_SECONDS`. An adapter returns `UP`,
   `NOT_FOUND` or `DOWN` — never a verdict.
5. **Compliance** (`services/compliance/service.py`) — builds `claimed` from the bid, `verified`
   from the portals, and a `context` of tender thresholds; runs the engine; writes one `Finding` per
   rule, each with exactly one `Evidence` row; scores the risk.
6. **Report / audit** (`services/reports/pdf_builder.py`, `services/audit/trail.py`) — a ReportLab
   PDF stamped with both document hashes, the rule pack name/version/SHA-256 and the engine version;
   every action appended to an immutable `AuditLog`.

Async is optional by design: `services/*/enqueue.py` dispatches to Celery when Redis is reachable
and otherwise runs the same function inline in the request. The demo needs no worker, no broker and
no network.

---

## 4. The eight problems, and the mechanism that answers each

### P1 — Manual claim verification is slow → *an adapter registry with a TTL cache*

**Implementation:** `services/verification/registry.py`, `adapters/`, `cache.py`

- `PortalAdapter` is one abstract method, `verify(**identifiers) -> VerificationOutcome`. Adding a
  portal is one file plus one registry entry.
- `verify_with_cache()` reuses any result for the same `(bid_id, portal)` inside the TTL, so
  re-running compliance after an officer edits a requirement costs zero portal calls — and cannot
  trip a real portal's rate limit.
- The whole GST + Udyam + debarment sweep for a bid is a single `POST /bids/{id}/verification`.

**Result:** the "open three portals and type an identifier" loop — the step officers skip under
deadline pressure — becomes one request whose result is stored, timestamped and auditable.

### P2 — Vendors overstate facts → *`source_priority` resolves the government record first*

**Implementation:** `services/rules/engine.py` (`_resolve_actual`), rule packs in `backend/rules/`

```yaml
- id: REQ-TURNOVER
  fact: financials.avg_annual_turnover
  operator: gte
  source_priority: [government, document]   # govt value beats claimed value
  threshold_from: tender.turnover_requirement
```

The engine maps `government → verified` and `document → claimed`, then walks `source_priority` in
order and takes the **first source that actually produced a value**. A government fact that came back
`DOWN` or `NOT_FOUND` is never placed in `verified` at all, so a missing key means "this source had
nothing" and the engine falls through to the next entry rather than inventing one.

**Result:** a bid claiming ₹6.2 Cr against a GST record of ₹4.1 Cr is judged on ₹4.1 Cr and fails —
and the finding carries *both* numbers (`claimed` and `verified` are stored side by side on every
`Finding`), so the officer sees the discrepancy, not just the verdict. This is the single mechanism
that turns a document reader into a fraud detector.

### P3 — "Where did this number come from?" → *evidence 1:1 with every finding, plus an append-only log*

**Implementation:** `models/finding.py`, `services/compliance/service.py` (`_resolve_evidence_fields`),
`services/audit/trail.py`, `routes/audit.py`

- `Evidence` has a unique FK to `Finding`: one finding, exactly one evidence row, enforced in the
  schema — `document_id`, `page_number`, `bbox`, verbatim `snippet`, and the document's SHA-256.
- `_resolve_evidence_fields()` picks the most specific real source available, in order: the bid page
  the fact was claimed on → the tender page the requirement came from → the tender document with the
  requirement text. There is no code path that writes a finding without a page.
- `AuditLog` rows are only ever appended — `record()` never updates or deletes — capturing actor,
  action, entity, and `before`/`after` for edits. Requirement edits store the full before/after
  snapshot, because a misread threshold silently produces a wrong verdict downstream.
- Every `Finding` is additionally stamped with `rule_pack_name`, `rule_pack_version`,
  `rule_pack_sha256` and `engine_version`, so a report filed today stays re-derivable after the pack
  is later edited.

**Result:** "why did this bid pass?" is answerable months later, down to the page, the snippet, the
exact rule pack bytes, and who ran it.

### P4 — Scanned and poor-quality PDFs → *OCR fallback that flags rather than fakes confidence*

**Implementation:** `services/ingestion/pdf_loader.py`, `ocr.py`, `pipeline.py`

- A page with fewer than 50 characters of embedded text is marked `needs_ocr` rather than trusted.
- OCR renders the page at 2× zoom, converts to grayscale, denoises (`fastNlMeansDenoising`),
  deskews via the minimum-area rectangle of the ink pixels, and adaptively thresholds before
  Tesseract sees it.
- Tesseract's mean word confidence below 40 sets `low_confidence = True` on the page. An OCR call
  that raises is caught: the page keeps whatever text existed and is marked low-confidence — a bad
  scan never crashes the job, and never silently passes as clean text.
- OCR word boxes are divided back down by the render zoom into PDF point space, so evidence
  highlighting works identically whether a page came from the text layer or from OCR.

**Result:** scanned bids are usable, and uncertainty is surfaced to the officer instead of hidden.

### P5 — Chaotic units and number formats → *exactly one normalization boundary*

**Implementation:** `services/extraction/normalizers.py`, `fact_normalization.py`

`normalize_amount()` handles the whole Indian-currency family — `₹5,00,00,000`, `Rs. 5 crore`,
`5 Cr`, `5,00,00,000/-`, `50 million`, `500 lakh` — stripping currency prefixes and `/-` / "only"
noise, then applying a unit multiplier table. Alongside it: `normalize_gstin` and `normalize_pan`
(format-validated, returning `None` on a malformed value rather than a wrong one), `normalize_date`
across eight common formats, and `normalize_years`.

`normalize_fact(fact_key, raw_value)` routes each fact key to the right normalizer by explicit key
sets (`_AMOUNT_KEYS`, `_BOOL_KEYS`, `_YEARS_KEYS`, `_GSTIN_KEYS`, `_PAN_KEYS`) and returns
`{"value": …, "unit": …}`. An unparseable string yields `value: None` — "extraction found something
unusable", which the compliance layer skips rather than guessing at.

**Result:** the rule engine only ever compares typed values. Nothing downstream parses a raw string.

### P6 — LLM hallucination would be fatal → *four independent guardrails*

**Implementation:** `services/llm/client.py`, `json_guard.py`, `extraction/snippet_guard.py`,
`rules/engine.py`

1. **Pinned sampling** — `OllamaClient` sends `temperature: 0, seed: 42` on every call, from the one
   place in the app that talks to a model.
2. **Forced, validated JSON** — `extract_structured()` requests `format: json`, validates against the
   Pydantic schema, and on a mismatch feeds the model its own bad output *plus the validation error
   plus the schema* and asks for a correction, up to `max_repairs` times. After that it raises
   `SchemaExtractionError` — it fails loudly rather than returning best-effort garbage.
3. **Snippet grounding** — `is_snippet_grounded()` accepts an extraction only if its quoted snippet
   appears verbatim (whitespace- and case-insensitive) in *that page's* text. Anything else is
   dropped with a warning before it can reach the database.
4. **Structural exclusion** — the model is not in the decision path at all. Even a grounded fact can
   only ever become an input to a deterministic rule, never a verdict.

**Result:** an invented eligibility requirement or an invented vendor claim cannot enter the legal
record. Covered by `tests/test_snippet_guard.py` and `tests/test_extraction.py`.

### P7 — Government portals are down or rate-limited → *degrade to `DOWN`, escalate to a human*

**Implementation:** `services/verification/base.py`, `adapters/gst.py`, `adapters/udyam.py`,
`adapters/mock_portal.py`, `registry.py`

- `VerificationOutcome.status` is `UP` | `NOT_FOUND` | `DOWN` — deliberately never `PASS` or `FAIL`.
  Judgement is not the verification layer's job.
- Adapters are contractually forbidden from raising on "not found" or "unreachable": an unset API
  key, a timeout, a 5xx and a transport error all map to `DOWN`, with the reason recorded in
  `raw_response`.
- A non-`UP` result contributes no fact, so the rule that needed it finds no value from any source
  and the engine emits **`NEEDS_REVIEW`** with a reason naming the fact and the sources tried.
- `VERIFICATION_MODE=mock` swaps the whole registry for JSON-file adapters
  (`data/mock_portals/*.json`), so the entire system runs with the network off. Debarment has no
  live adapter in either mode — deliberately, so a missing live source degrades to `NEEDS_REVIEW`
  rather than silently skipping the debarment check.

**Result:** an outage produces an escalation, never a false PASS or a false FAIL.

### P8 — Ambiguous legal language → *a fixed taxonomy with an explicit "human must read this" bucket*

**Implementation:** `models/requirement.py`, `services/compliance/requirement_binding.py`,
`services/rules/condition.py`, `services/compliance/service.py`

- Requirements are bucketed into a fixed taxonomy: `turnover | experience | certification |
  registration | financial | technical | msme | debarment | manual_review`. Anything that does not
  map cleanly lands in `manual_review` — a visible bucket, not a guess.
- `match_rule_for_extracted()` binds an extracted requirement to a rule pack entry only on a
  confident match; with no match it leaves `external_ref = None` rather than binding to the wrong
  rule.
- `_uncovered_requirements()` then turns every tender requirement that no rule judges into a
  **weight-0 `NEEDS_REVIEW` finding**: visible on the compliance matrix, but structurally unable to
  move the risk score on its own. Silently dropping these would have looked like full coverage.
- Conditional clauses are `applies_if` expressions — `bid.claims_msme_benefit == true` — parsed by a
  deliberately tiny fixed grammar (`<fact.path> <op> <literal>`). **Never `eval()`**: rule packs are
  officer-editable data, and data must not be able to execute code.

**Result:** an unclear clause is escalated, never force-fitted.

---

## 5. Where the engine says "I am not sure"

Correctness here is mostly about refusing to guess. The engine emits `NEEDS_REVIEW` — and contributes
**half** the rule's weight to risk, rather than zero or full — in exactly four situations:

| Situation | Trigger in `engine.py` | Why it isn't a FAIL |
|---|---|---|
| The tender threshold this rule compares against was never extracted | `threshold_from` key missing from `context` | Nothing is known about the bar; failing the vendor would be arbitrary |
| No source produced a value for the fact | every entry in `source_priority` empty | Absence of evidence is not evidence of ineligibility |
| The bid states **different values for the same fact on different pages** | `FactValue.conflicts` non-empty | An internal contradiction is itself the signal — judging whichever page loaded last would be confidently wrong |
| The comparison itself is not evaluable | operator raises `TypeError` / `ValueError` | A type mismatch is a data problem, not a vendor problem |

The conflict case is worth stating plainly: `_build_claimed()` groups every claimed fact by key, and
when the bid asserts more than one distinct value for a key it attaches **every page-cited variant**
to the fact, forcing the engine to escalate. A bid claiming ₹6.2 Cr on page 3 and ₹4.9 Cr on page 11
does not get a verdict; it gets an officer.

The same instinct governs `_build_context()`: a per-requirement namespaced key
(`tender.REQ-TURNOVER.value`) is always populated, while the legacy category-wide key
(`tender.turnover_requirement`) is populated **only when every requirement in that category agrees on
one value**. Two differently-valued requirements colliding on one category drop the shared key
entirely, which surfaces as `NEEDS_REVIEW` instead of a silent pick.

---

## 6. Risk scoring: weighted, with a floor a single blocker cannot be diluted below

`services/risk/scorer.py` computes `score = Σ risk_contribution / Σ weight × 100` (0–100, higher =
riskier) and bands it `LOW ≤ 33 < MEDIUM ≤ 65 < HIGH`, with one override: **any FAILed
`BLOCKER`-severity finding forces the HIGH band and a score floor of 66**, reported as
`forced_by_blocker: true`.

A debarred vendor is disqualified. It should not be possible for twenty-six unrelated passes to
average that away — so the aggregation cannot.

---

## 7. Failure modes, and what each one produces

| If this fails… | The system does this | Never this |
|---|---|---|
| Portal down / no API key / timeout | `status = DOWN` → finding `NEEDS_REVIEW` | A false PASS or FAIL |
| OCR raises on a page | Page kept, `low_confidence = True`, ingest continues | Whole document marked failed |
| Vector index build fails | Logged; ingest still `done` (retrieval is an enhancement) | An otherwise-good ingest marked failed |
| LLM returns unparseable JSON | Repair loop, then `SchemaExtractionError` | Best-effort garbage persisted |
| LLM quotes a snippet not on the page | Extraction dropped with a warning | An ungrounded fact in the database |
| Redis unreachable | The same work runs inline in the request | The endpoint failing |
| Bad UUID in the path | `400 INVALID_ID` via `parse_uuid()` | An unhandled `ValueError` surfacing as a 500 |
| Duplicate upload (same bytes, same kind) | Existing document reused, `duplicate: true` | A second copy re-ingested |
| Rule pack malformed | `INVALID_RULE_PACK` naming the rule **and the YAML line number** | A partially loaded pack |
| Unknown procurement category | Falls back to `default_goods.yaml` | No check at all |
| Compliance re-run | Old findings deleted, fresh set written — the matrix is a live view | Stale rows accumulating |

Every domain error leaves through one envelope — `{code, message, detail}` — from the handlers
registered in `core/errors.py`, so the frontend has exactly one error shape to render.

---

## 8. Determinism and provenance: what is pinned, hashed and stamped

| Artefact | Recorded as | So that… |
|---|---|---|
| Uploaded document | SHA-256 on the `Document` row, inside every `Evidence` row, and in the report | The PDF a verdict was based on is provably the PDF you are holding |
| Rule pack | SHA-256 of the raw YAML text, plus name and version, on **every** `Finding` | A pack edited next month cannot retroactively rewrite what a filed report meant |
| Engine behaviour | `ENGINE_VERSION` (currently `1.0.0`), bumped whenever engine semantics could shift a verdict | A re-run under changed semantics is distinguishable from the original |
| LLM sampling | `temperature: 0`, `seed: 42` | Re-extraction reproduces the same facts |
| Verification result | Portal, status, normalized payload, raw response, `fetched_at` | The government record *as it was on the day*, not as it is now |
| Every action | `AuditLog` row: actor, action, entity, before/after, timestamp | The decision history is reconstructable |

---

## 9. How the solution is verified

**95 backend tests, all passing.** Coverage by area:

| Test file | What it pins down |
|---|---|
| `test_rules_engine.py` (8) | Verdict logic, `source_priority` resolution, conflict escalation, unresolvable thresholds |
| `test_compliance_service.py` (4) | The finding↔evidence invariant, the uncovered-requirement bucket, re-run replacement |
| `test_snippet_guard.py` (6) | Ungrounded extractions are rejected |
| `test_extraction.py` (6), `test_extraction_glue.py` (7), `test_extraction_routes.py` (2) | Schema guard, repair loop, persistence idempotency, the extract endpoints |
| `test_fact_normalization.py` (3) | The messy-number boundary |

Reproduce end to end without a network:

```bash
# from backend/
.venv/Scripts/python.exe -m pytest -q          # 95 passed

# from the project root
python scripts/generate_sample_pdfs.py         # sample tender + bid PDFs
python scripts/load_sample_data.py             # seed → verify → compliance
python scripts/run_pipeline_cli.py             # end-to-end JSON findings, no API or UI needed
```

`VERIFICATION_MODE=mock` plus a local Ollama model means the full demo runs with WiFi switched off.

### Success criteria from `problem.md` §9

| Criterion | Status |
|---|---|
| A full compliance matrix with no manual portal lookups | ✅ End-to-end |
| Every verdict cites a page and a snippet | ✅ Schema-enforced 1:1 `Finding`↔`Evidence` |
| The same documents always produce the same verdict | ✅ Pure engine, temp 0, pinned seed, covered by tests |
| An inflated claim is caught against the government record | ✅ `source_priority`, demonstrated on the fixture |
| A portal outage never yields a false PASS/FAIL | ✅ `DOWN` → `NEEDS_REVIEW` |
| The whole demo runs offline | ✅ Mock mode + local Ollama |
| A hallucinated extraction cannot reach the database | ✅ `snippet_guard` + tests |
| ~80% less verification effort | ⚠️ **Still unmeasured** — see §10.4 |

---

## 10. Solutions to what is *not* yet solved

`problem.md` §10 lists the honest gaps. Each has a designed answer below; this section is the plan of
record, not a claim of completion.

### 10.1 Access control (S1–S5) — the one blocking gap

The whole auditability claim rests on knowing who acted. Today `core/deps.py:get_actor()` reads a
client-controlled `X-Actor` header and defaults to `"officer"` — fine for a single-user demo,
forgeable in a deployment.

**The fix, in dependency order:**

| Step | Change | Closes |
|---|---|---|
| 1 | A `User` model (id, email, hashed password, role ∈ `officer` / `reviewer` / `admin`, department) plus an Alembic migration | — |
| 2 | OAuth2 password flow issuing a short-lived JWT; a `get_current_user()` dependency; router-level `Depends` on every non-health route | **S1** |
| 3 | `get_actor()` returns `current_user.email` instead of reading the header — **the one-line change that makes the audit trail unforgeable** | **S3** |
| 4 | Scope tenders and bids to a department; replace the bare `db.get(Bid, …)` in routes with a `get_bid_for_actor()` dependency that 404s (not 403s) on another department's UUID | **S2** |
| 5 | Put `GET /bids/{id}/report` behind the same dependency — it is currently the most exposed endpoint, streaming a full compliance PDF to anyone holding the UUID | **S5** |
| 6 | Encrypt uploads at rest (AES-GCM, key from environment or OS keystore), tighten `data/uploads` permissions, and serve PDFs only through an authenticated streaming endpoint rather than a path | **S4** |

Steps 1–3 are the minimum for the audit trail to mean anything; 4–6 are the minimum for a
deployment. The route layer is already uniform — every handler takes `db` and `actor` by dependency
— so this is additive, not a refactor.

### 10.2 Functional gaps

| Gap | Designed solution | Notes |
|---|---|---|
| **No multi-bid comparison** — the real question is "which of these eight qualifies?" | `GET /tenders/{id}/comparison`: aggregate the already-persisted `Finding` rows for every bid on the tender into a requirement × vendor grid, ranked by band, then fail count, then risk score | Pure read-side aggregation over rows that already exist. No engine change and no new verdict logic — which is exactly why it is the highest value-per-risk feature left |
| **No officer review step in the UI** | `human_reviewed`, `reviewed_by`, `reviewed_at` and the audited `PATCH /tenders/{id}/requirements/{rid}` already exist and work. Add the toggle to the Requirements page and, behind a setting, warn or block on running compliance with unreviewed requirements | Until that screen exists, drop "officer review" from the hallucination-countermeasure list — the claim currently outruns the UI |
| **Semantic clause search is invisible** | `GET /tenders/{id}/search` is implemented and working. Surface it as a search box on the Requirements and Evidence pages, and document it in `docs/api.md` | Pure surfacing; the retrieval stack (MiniLM, 384-dim, FAISS with a NumPy fallback) is already in place |
| **No rule pack editor** | `PUT /rules/{category}` that runs the candidate YAML through `load_rule_pack()` as the validation gate — it already reports the offending rule id *and* line number — rejects on failure, bumps `version`, writes the file, and logs an audit entry with before/after | The validator is the hard part, and it exists. "Officer-editable" becomes true in practice, not just in principle |
| **No finding override** | A `FindingOverride` row (finding_id, actor, new_status, justification, timestamp) rather than mutating the `Finding`. The matrix shows the engine verdict *and* the override side by side | Never overwrite an engine verdict — determinism means the engine's output must stay re-derivable. An override is a second, attributed opinion |

### 10.3 Edge-case hardening

| Case | Fix |
|---|---|
| A non-PDF renamed to `.pdf` | Check the `%PDF-` magic bytes in `validate_pdf_upload()`, not just the extension |
| Password-protected PDF | Detect `doc.needs_pass` in `pdf_loader.extract_pdf()` → `status = failed` with a clear reason |
| Untrusted PDF resource exhaustion | A page-count ceiling and a per-document processing timeout in the ingestion pipeline |
| Report requested before compliance ran | Already handled — `404 NOT_RUN` |
| Two officers running compliance on one bid concurrently | Last write wins today. Take a row lock (or a per-bid advisory lock) around the delete-then-write in `run_compliance()` |
| No rate limiting anywhere | `slowapi` limits on the upload, extract and verification endpoints — the three that cost real CPU or real portal quota |

### 10.4 The unmeasured claim

"~80% less verification effort" has no benchmark in the repo, and until it does it should be
described as a target rather than a result. The measurement that would settle it: time a procurement
officer manually verifying a fixed set of *n* bids against *m* criteria, then time the same officer
reviewing TenderGuard's matrix for the same set — comparing wall-clock minutes and, separately,
agreement between the two verdict sets. Publish both numbers, including the disagreements.

### 10.5 Documentation contradictions

| Contradiction | Resolution |
|---|---|
| `docs/api.md` says there is no `/audit` list endpoint; `routes/audit.py` implements one | Stale doc — document the endpoint, and `GET /tenders/{id}/search` with it |
| README and `.env.example` specify `llama3.1:8b`; the working `.env` uses `qwen2.5:3b` | Declare `llama3.1:8b` canonical for quality claims, note `qwen2.5:3b` as the documented hardware-constrained local default, and state which one any given demo ran on |
| `CLAUDE.md` presents Docker Compose as the one-command path, but Docker is not installed here | Mark the compose path "correct by inspection, never executed on this machine"; the SQLite + native Ollama path is the one actually exercised |

---

## 11. What we deliberately did not build

Blockchain · multi-agent orchestration · a chatbot interface · custom model training · Kubernetes ·
heavy RAG infrastructure · integrations with ten different portals.

The restraint is the point. The problem is solved by **determinism and provenance**, not by more AI —
and every one of those additions would have traded away one of the two.

---

## 12. Traceability: problem → mechanism → code → test

| Problem | Mechanism | Code | Test |
|---|---|---|---|
| P1 Slow manual verification | Adapter registry + TTL cache | `services/verification/{registry,cache}.py` | Exercised through the compliance tests' mock adapters |
| P2 Overstated claims | `source_priority: [government, document]` | `services/rules/engine.py::_resolve_actual` | `test_rules_engine.py` |
| P3 Unauditable verdicts | 1:1 `Finding`↔`Evidence` + append-only `AuditLog` | `models/finding.py`, `compliance/service.py`, `audit/trail.py` | `test_compliance_service.py` |
| P4 Scanned PDFs | 50-char threshold → OCR, `low_confidence` | `ingestion/{pdf_loader,ocr,pipeline}.py` | Manual, against the sample PDFs |
| P5 Messy units | One normalization boundary | `extraction/{normalizers,fact_normalization}.py` | `test_fact_normalization.py` |
| P6 Hallucination | temp 0 + seed · JSON guard · snippet guard · no LLM in decisions | `llm/{client,json_guard}.py`, `extraction/snippet_guard.py` | `test_snippet_guard.py`, `test_extraction.py` |
| P7 Portal downtime | `DOWN` → `NEEDS_REVIEW`; adapters never raise | `verification/base.py`, `adapters/*` | `test_rules_engine.py` (missing-source path) |
| P8 Ambiguous language | Fixed taxonomy · `manual_review` · `applies_if` grammar, never `eval()` | `rules/condition.py`, `compliance/requirement_binding.py` | `test_rules_engine.py`, `test_extraction_glue.py` |

---

**Bottom line:** every problem in `problem.md` §5 has a mechanism in this codebase, and the
mechanisms share one shape — *extract with a model, decide with a function, cite everything, and
escalate rather than guess*. The remaining work is not more intelligence; it is **access control**
(§10.1), after which the same system becomes deployable rather than merely demonstrable.
