# TenderGuard — AI Tender & Vendor Compliance Verification

**SIH26100 — Automated verification of vendor bids against tender requirements + government records.**

An officer uploads a **tender document** and a **vendor bid**. The system extracts the tender's
eligibility requirements, extracts the vendor's claimed facts, verifies those facts against
**government portals**, applies a **deterministic rule engine**, and produces a
**compliance matrix with evidence, risk score and a PDF report** — where every
PASS / FAIL / NEEDS-REVIEW can be traced back to a page and a line.

> The differentiator is **not** "PDF → OCR → ChatGPT → answer".
> It is **Document AI + Government verification + deterministic rules + evidence + risk + audit trail**.

---

## 1. The one sentence that wins the demo

> "Officer, this bid failed on 3 of 27 criteria. Here is the exact clause in the tender,
> the exact line in the bid, and the exact government record that contradicts it."

Judges trust what they can **verify on screen**. Build for that.

---

## 2. System architecture

```
                          ┌──────────────────────┐
                          │   Officer Dashboard  │
                          └──────────┬───────────┘
                                     │  upload
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
              Tender PDF                        Vendor Bid PDF
                     │                               │
                     ▼                               ▼
          ┌────────────────────┐          ┌────────────────────┐
          │  INGESTION LAYER   │          │  INGESTION LAYER   │
          │  PyMuPDF + OCR     │          │  PyMuPDF + OCR     │
          │  (page, bbox kept) │          │  (page, bbox kept) │
          └─────────┬──────────┘          └─────────┬──────────┘
                    ▼                               ▼
          ┌────────────────────┐          ┌────────────────────┐
          │ Requirement AI     │          │ Vendor Fact AI     │
          │ LLM → structured   │          │ LLM → structured   │
          │ requirement list   │          │ claimed facts      │
          └─────────┬──────────┘          └─────────┬──────────┘
                    │                               │
                    │        ┌──────────────────────┘
                    │        │
                    │        ▼
                    │   ┌──────────────────────────────────┐
                    │   │   GOVERNMENT VERIFICATION LAYER  │
                    │   │   GST · Udyam · PAN · MCA · EPFO │
                    │   │   (adapter pattern + mock mode)  │
                    │   └────────────────┬─────────────────┘
                    │                    │
                    └──────────┬─────────┘
                               ▼
                    ┌─────────────────────┐
                    │   RULE ENGINE       │
                    │  deterministic YAML │
                    │  no LLM decisions   │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │  COMPLIANCE MATRIX  │
                    └──────────┬──────────┘
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
         EVIDENCE          RISK SCORE       AUDIT TRAIL
        (page + bbox)      (weighted)      (append-only)
              └────────────────┼────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │  Officer Dashboard  │
                    │   + PDF Report      │
                    └─────────────────────┘
```

**Golden rule of this architecture:** the LLM **extracts**, it never **decides**.
Decisions come from the rule engine, so they are reproducible, explainable and auditable.

---

## 3. Folder structure

```
tenderguard/
│
├── README.md
├── docker-compose.yml
│
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   │
│   ├── app/



│   │   ├── main.py                  # FastAPI entrypoint
│   │   ├── config.py                # pydantic-settings, reads .env
│   │   │
│   │   ├── api/v1/routes/
│   │   │   ├── health.py
│   │   │   ├── tenders.py           # upload tender, list requirements
│   │   │   ├── bids.py              # upload bid, list extracted facts
│   │   │   ├── verification.py      # trigger / read govt verification
│   │   │   ├── compliance.py        # run engine, get compliance matrix
│   │   │   └── reports.py           # download PDF report
│   │   │
│   │   ├── core/
│   │   │   ├── logging.py           # structlog, request ids
│   │   │   ├── deps.py              # DB session, auth dependencies
│   │   │   └── errors.py            # unified error envelope
│   │   │
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   ├── base.py
│   │   │   └── migrations/          # alembic
│   │   │
│   │   ├── models/                  # SQLAlchemy tables
│   │   │   ├── tender.py
│   │   │   ├── vendor.py
│   │   │   ├── document.py          # file + page-level text store
│   │   │   ├── requirement.py
│   │   │   ├── verification.py      # one row per portal check
│   │   │   ├── finding.py           # one row per rule result
│   │   │   └── audit_log.py
│   │   │
│   │   ├── schemas/                 # pydantic request/response models
│   │   │
│   │   ├── services/
│   │   │   ├── ingestion/
│   │   │   │   ├── pdf_loader.py    # text + page + bbox extraction
│   │   │   │   ├── ocr.py           # tesseract fallback for scans
│   │   │   │   └── layout.py        # table / section detection
│   │   │   │
│   │   │   ├── extraction/
│   │   │   │   ├── tender_requirements.py   # tender → requirement objects
│   │   │   │   ├── vendor_facts.py          # bid → claimed fact objects
│   │   │   │   └── normalizers.py           # crore→number, dates, GSTIN
│   │   │   │
│   │   │   ├── llm/
│   │   │   │   ├── client.py        # Ollama HTTP client, retry, timeout
│   │   │   │   ├── json_guard.py    # force + validate JSON output
│   │   │   │   └── prompts/
│   │   │   │       ├── requirement_extraction.txt
│   │   │   │       ├── vendor_fact_extraction.txt
│   │   │   │       └── explanation.txt
│   │   │   │
│   │   │   ├── retrieval/
│   │   │   │   ├── chunker.py       # section-aware chunks, keeps page no
│   │   │   │   ├── embeddings.py    # sentence-transformers
│   │   │   │   ├── vector_store.py  # FAISS index per document
│   │   │   │   └── search.py        # "find the clause that proves X"
│   │   │   │
│   │   │   ├── verification/
│   │   │   │   ├── base.py          # PortalAdapter interface
│   │   │   │   ├── registry.py      # mode switch: mock | live
│   │   │   │   └── adapters/
│   │   │   │       ├── gst.py
│   │   │   │       ├── udyam.py
│   │   │   │       ├── pan.py
│   │   │   │       ├── mca.py
│   │   │   │       ├── epfo.py
│   │   │   │       └── mock_portal.py   # offline demo data
│   │   │   │
│   │   │   ├── rules/
│   │   │   │   ├── engine.py        # evaluates rule pack vs facts
│   │   │   │   ├── loader.py        # YAML → Rule objects
│   │   │   │   └── operators.py     # gte, lte, eq, in, regex, date_before
│   │   │   │
│   │   │   ├── risk/
│   │   │   │   ├── scorer.py        # weighted 0–100 risk score
│   │   │   │   └── weights.py       # criticality per requirement type
│   │   │   │
│   │   │   ├── evidence/
│   │   │   │   ├── collector.py     # attach source snippet to each finding
│   │   │   │   └── provenance.py    # doc id + page + bbox + hash
│   │   │   │
│   │   │   ├── reports/
│   │   │   │   ├── pdf_builder.py   # ReportLab
│   │   │   │   └── templates/
│   │   │   │
│   │   │   └── audit/
│   │   │       └── trail.py         # append-only action log
│   │   │
│   │   └── workers/
│   │       ├── celery_app.py
│   │       └── tasks.py             # long OCR / extraction jobs
│   │
│   ├── rules/                       # rule packs (versioned YAML)
│   │   ├── default_goods.yaml
│   │   ├── default_works.yaml
│   │   └── default_services.yaml
│   │
│   └── tests/
│       ├── fixtures/                # small deterministic PDFs + JSON
│       ├── test_rules_engine.py
│       ├── test_extraction.py
│       ├── test_verification.py
│       └── test_api.py
│
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   ├── public/
│   └── src/
│       ├── api/client.js            # axios wrapper
│       ├── store/                   # global state
│       ├── pages/
│       │   ├── Upload.jsx           # tender + bid upload
│       │   ├── Requirements.jsx     # extracted requirements review/edit
│       │   ├── ComplianceMatrix.jsx # the money screen
│       │   ├── EvidenceViewer.jsx   # PDF page + highlighted snippet
│       │   └── Reports.jsx
│       └── components/
│           ├── compliance/
│           │   ├── StatusChip.jsx   # PASS / FAIL / REVIEW
│           │   ├── RiskGauge.jsx
│           │   └── FindingRow.jsx
│           └── common/
│
├── data/
│   ├── samples/
│   │   ├── tenders/                 # 3–5 real public tender PDFs
│   │   └── bids/                    # matching synthetic vendor bids
│   ├── mock_portals/                # GST/Udyam/PAN JSON for offline demo
│   ├── uploads/                     # runtime (gitignored)
│   └── vectorstore/                 # FAISS indexes (gitignored)
│
├── docs/
│   ├── architecture.md
│   ├── rule_pack_spec.md
│   ├── api.md
│   └── demo_script.md
│
├── infra/
│   ├── nginx/nginx.conf
│   └── docker-compose.yml
│
└── scripts/
    ├── seed_mock_portals.py
    ├── load_sample_data.py
    └── run_pipeline_cli.py          # end-to-end without the UI
```

---

## 4. Tech stack

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI + Uvicorn | async, auto OpenAPI docs, fast to build |
| DB | PostgreSQL + SQLAlchemy + Alembic | relational compliance data, real audit trail |
| Jobs | Celery + Redis | OCR and extraction are slow, must not block upload |
| PDF text | PyMuPDF + pdfplumber | text, page numbers, bounding boxes, tables |
| OCR | Tesseract (pytesseract) + OpenCV | scanned tenders are common |
| LLM | **Ollama + Llama 3.1 8B** (local) | offline demo, no API cost, data never leaves the machine |
| Embeddings | sentence-transformers (MiniLM) | cheap, fast, good enough for clause retrieval |
| Vector store | FAISS (local file per doc) | no extra service to run |
| Rules | YAML rule packs + custom engine | deterministic, explainable, editable by officers |
| Reports | ReportLab | proper government-style PDF |
| Frontend | React + Vite + Tailwind | fast build, clean dashboard |
| Deploy | Docker Compose + Nginx | single `docker compose up` demo |

---

## 5. Core data model

```
tender ──1:N── requirement
   │                │
   │                └──1:N── finding ──1:1── evidence
   │                            │
vendor ──1:N── bid ──1:N── claimed_fact
   │
   └──1:N── verification_result   (portal, status, raw_response, fetched_at)

audit_log  (actor, action, entity, before, after, timestamp)   # append-only
```

**Finding** is the heart of the system:

```json
{
  "requirement_id": "REQ-014",
  "requirement_text": "Bidder must have average annual turnover >= 5 Cr in last 3 FY",
  "expected": { "operator": "gte", "value": 50000000, "unit": "INR" },
  "claimed":  { "value": 62000000, "source": { "doc": "bid.pdf", "page": 12, "bbox": [72, 340, 520, 366] } },
  "verified": { "value": 41000000, "source": { "portal": "GST", "fetched_at": "2026-08-29T10:14:00Z" } },
  "status": "FAIL",
  "reason": "Government-verified turnover is below the tender threshold",
  "severity": "CRITICAL",
  "risk_contribution": 25
}
```

Note that **claimed** and **verified** are stored separately. That gap is the fraud signal, and
it is what a basic team will never show.

---

## 6. Rule pack format

`backend/rules/default_goods.yaml`

```yaml
version: 1
name: Default Goods Procurement Pack
rules:
  - id: REQ-TURNOVER
    label: Minimum average annual turnover
    severity: CRITICAL
    weight: 25
    fact: financials.avg_annual_turnover
    operator: gte
    source_priority: [government, document]   # govt value beats claimed value
    threshold_from: tender.turnover_requirement

  - id: REQ-GST-ACTIVE
    label: GST registration must be active
    severity: CRITICAL
    weight: 20
    fact: gst.status
    operator: eq
    value: ACTIVE
    source_priority: [government]

  - id: REQ-MSME
    label: Udyam certificate valid if claiming MSME benefit
    severity: MAJOR
    weight: 10
    fact: udyam.valid
    operator: eq
    value: true
    applies_if: bid.claims_msme_benefit == true

  - id: REQ-DEBARMENT
    label: Vendor must not be debarred / blacklisted
    severity: BLOCKER
    weight: 40
    fact: debarment.listed
    operator: eq
    value: false
    source_priority: [government]
```

Rules are **data, not code**. An officer can add a criterion without a developer.
That single fact scores heavily on *sustainability* and *future scalability* in SIH judging.

---

## 7. Build order — step by step

Build **vertically**, not horizontally. One thin end-to-end path first, then widen it.

### Phase 0 — Foundation (Day 1)
Repo, docker-compose (postgres + redis + ollama), FastAPI skeleton, `/health`, React shell.
**Exit test:** `docker compose up` → API docs open, UI loads, DB connects.

### Phase 1 — Ingestion (Day 2–3)
Upload PDF → store file → extract text per page with page number and bbox → save to DB.
OCR fallback when a page has under ~50 characters of embedded text.
**Exit test:** upload a scanned tender, get readable text with correct page numbers.

### Phase 2 — Requirement extraction (Day 4–5)
Chunk the tender, prompt the local LLM, force JSON output, validate against a Pydantic schema,
store requirement rows. Show them in the UI and **let the officer edit them**.
**Exit test:** a real tender PDF produces 15+ usable requirements, each with a page reference.

### Phase 3 — Vendor fact extraction (Day 6)
Same pipeline on the bid: GSTIN, PAN, Udyam number, turnover per FY, experience, certificates.
Normalize units (lakh / crore / commas / symbols) before storing.
**Exit test:** every extracted fact carries a page number and a verbatim snippet.

### Phase 4 — Government verification (Day 7–8)
Adapter interface + **mock mode first** (JSON files in `data/mock_portals/`).
Then wire 2 real portals. Cache every response with `fetched_at`.
**Exit test:** flipping `VERIFICATION_MODE=mock|live` works both ways; the demo never breaks offline.

### Phase 5 — Rule engine + risk (Day 9–10)
YAML loader, operators, evaluation producing findings, weighted risk score 0–100.
**Zero LLM calls in this layer.**
**Exit test:** same input → byte-identical findings, every single run.

### Phase 6 — Evidence + dashboard (Day 11–12)
Compliance matrix table, status chips, risk gauge, and **click a finding → the PDF page opens with
the source snippet highlighted**. This screen wins the demo.
**Exit test:** a judge can click any FAIL and see the proof in under 3 seconds.

### Phase 7 — Report + audit (Day 13)
ReportLab PDF: summary, compliance matrix, evidence appendix, verification timestamps, document hashes.
Append-only audit log of every action.
**Exit test:** the downloaded PDF is something an officer could actually file.

### Phase 8 — Hardening + demo rehearsal (Day 14)
Seed data, reset script, 5-minute scripted demo, offline fallback for everything.

---

## 8. Issue board — one issue, one working unit

Each issue is small enough for one person to finish and merge on its own.
The **Dep** column is the issue number it depends on.

### Epic A — Foundation

| # | Issue | Acceptance criteria | Dep |
|---|---|---|---|
| 1 | Repo + docker-compose (api, postgres, redis, ollama, nginx) | `docker compose up` starts all 5, `/health` returns 200 | — |
| 2 | `config.py` with pydantic-settings + `.env.example` | Missing required env fails fast with a clear message | 1 |
| 3 | SQLAlchemy base + Alembic initial migration | `alembic upgrade head` creates all tables | 2 |
| 4 | structlog logging + request-id middleware | Every log line carries a request id | 2 |
| 5 | Unified error envelope + global exception handler | All errors return `{code, message, detail}` | 2 |
| 6 | React + Vite + Tailwind shell with routing | 5 routes render, API base URL from env | 1 |

### Epic B — Document ingestion

| # | Issue | Acceptance criteria | Dep |
|---|---|---|---|
| 7 | `POST /tenders` upload with size + MIME validation | Rejects >50 MB and non-PDF with a 4xx | 3 |
| 8 | `pdf_loader.py` — text per page with bbox | Returns page no + text + bbox for a digital PDF | 7 |
| 9 | `ocr.py` — Tesseract fallback + deskew/denoise | A scanned page yields text; fallback triggers automatically | 8 |
| 10 | `layout.py` — section headings + table detection | The eligibility section is identified in 3+ sample tenders | 8 |
| 11 | Document + page persistence, SHA-256 file hash | Re-uploading the same file is detected as a duplicate | 8 |
| 12 | Celery ingestion task + job status endpoint | Upload returns `job_id` instantly, status polls to `done` | 11 |

### Epic C — Retrieval

| # | Issue | Acceptance criteria | Dep |
|---|---|---|---|
| 13 | `chunker.py` — section-aware chunks that keep page numbers | No chunk loses its page reference | 10 |
| 14 | `embeddings.py` — MiniLM, batched, cached | A 200-page doc embeds in under 60 s on CPU | 13 |
| 15 | `vector_store.py` — FAISS index per document, persisted | The index survives a restart | 14 |
| 16 | `search.py` — top-k clause search with scores | Query "turnover requirement" returns the right clause in the top 3 | 15 |

### Epic D — LLM extraction

| # | Issue | Acceptance criteria | Dep |
|---|---|---|---|
| 17 | Ollama client: timeout, retry, streaming off | Survives a model cold start without failing the request | 2 |
| 18 | `json_guard.py` — schema-constrained JSON + repair loop | 20/20 test prompts return schema-valid JSON | 17 |
| 19 | Requirement extraction prompt + Pydantic schema | 15+ requirements from a real tender, each with a page ref | 18, 16 |
| 20 | Officer edit/approve requirements API + UI | Edits persist and are marked `human_reviewed` | 19, 6 |
| 21 | Vendor fact extraction (GSTIN, PAN, Udyam, turnover, experience) | Each fact has value + page + snippet | 18 |
| 22 | `normalizers.py` — lakh/crore, dates, GSTIN regex | Unit tests cover 30 messy real-world strings | 21 |

### Epic E — Government verification

| # | Issue | Acceptance criteria | Dep |
|---|---|---|---|
| 23 | `PortalAdapter` base interface + `registry.py` mode switch | Adding a portal = adding one file, no core edits | 3 |
| 24 | `mock_portal.py` + `seed_mock_portals.py` | The full demo runs with zero internet | 23 |
| 25 | GST adapter (status, filing history, turnover band) | Returns a normalized dict; failures degrade to `UNVERIFIED` | 23 |
| 26 | Udyam adapter (MSME validity, category) | Same contract as the GST adapter | 23 |
| 27 | Verification cache + `fetched_at` + rate limiting | A repeat check within TTL does not hit the portal | 25 |
| 28 | Verification result persistence + raw response storage | Raw payload retained for audit | 27 |

### Epic F — Rules, risk, evidence

| # | Issue | Acceptance criteria | Dep |
|---|---|---|---|
| 29 | YAML rule loader + validation | A malformed rule pack fails at load with a line number | 3 |
| 30 | `operators.py` (gte, lte, eq, in, regex, date_before, exists) | 100% unit test coverage on operators | 29 |
| 31 | `engine.py` — evaluate rules over claimed + verified facts | Deterministic: same input → identical output, 10/10 runs | 30, 28, 22 |
| 32 | `source_priority` resolution (government beats document) | Claimed 6 Cr vs verified 4 Cr → FAIL, both values shown | 31 |
| 33 | Risk scorer — weighted 0–100 + band (LOW/MED/HIGH) | One BLOCKER forces HIGH regardless of other passes | 31 |
| 34 | Evidence collector — snippet + page + bbox on every finding | No finding can be saved without a source reference | 31 |

### Epic G — Dashboard

| # | Issue | Acceptance criteria | Dep |
|---|---|---|---|
| 35 | Compliance matrix table with filters and status chips | 27 findings render; filter by FAIL works | 31, 6 |
| 36 | Risk gauge + summary header | Score, band, counts of pass / fail / review | 33 |
| 37 | Evidence viewer — PDF page render + highlighted bbox | Clicking a finding scrolls to and highlights the source | 34 |
| 38 | Side-by-side claimed vs verified comparison view | Mismatches visually flagged in red | 32 |

### Epic H — Report, audit, polish

| # | Issue | Acceptance criteria | Dep |
|---|---|---|---|
| 39 | ReportLab report (summary + matrix + evidence appendix) | PDF opens cleanly, includes doc hashes and timestamps | 34 |
| 40 | Append-only audit log + `/audit` view | Every upload, edit, verification and report is logged | 5 |
| 41 | `run_pipeline_cli.py` end-to-end without the UI | One command: tender + bid → JSON findings | 31 |
| 42 | Demo seed + reset script | `python scripts/load_sample_data.py` gives a full demo state | 24 |
| 43 | `docs/demo_script.md` — 5-minute script | Rehearsed twice, fits in 5 minutes | 42 |

**Suggested 5-person split**
Ingestion + OCR (B) · LLM extraction (C + D) · Verification + Rules (E + F) · Frontend (G) ·
Reports + DevOps + Demo (A + H).

---

## 9. Known hard problems and how to handle them

These are the things that actually break this project. Plan for them now, not on day 12.

**1. Scanned tenders produce garbage text.**
Handle: detect low text density per page → OCR fallback → deskew and denoise in OpenCV → if OCR
confidence is still low, mark the page `LOW_CONFIDENCE` and surface it to the officer instead of
silently guessing. Never let bad OCR turn into a silent FAIL.

**2. The LLM hallucinates requirements or numbers.**
Handle: (a) the LLM only extracts, it never decides; (b) every extracted field must carry a page and
a verbatim snippet, and you **reject any extraction whose snippet is not literally present in the
source text**; (c) an officer review step before the rule engine runs. Hallucination becomes
visible instead of fatal.

**3. Government portals have captchas, rate limits, and downtime.**
Handle: adapter pattern plus `VERIFICATION_MODE=mock` from day one. Cache aggressively with
`fetched_at`. On failure the status is `UNVERIFIED` — never `PASS`, never `FAIL` — and the finding
becomes NEEDS-REVIEW. **Your demo must run with the wifi switched off.**

**4. Requirements are written in ambiguous legal language.**
Handle: map extracted requirements onto a fixed taxonomy (turnover, experience, certification,
registration, financial, technical). Anything unmapped goes into a `MANUAL_REVIEW` bucket rather
than being force-fitted into a rule.

**5. Units and formats are chaotic.** ("Rs. 5,00,00,000", "5 Crore", "5cr", "50 million")
Handle: one `normalizers.py`, tested against 30 real strings, applied at the boundary. Never compare
raw strings inside the rule engine.

**6. Deterministic output is required for trust.**
Handle: LLM temperature 0, seed pinned, extraction cached by document hash. Judges may run the same
document twice — the answer must not change.

**7. Long documents blow up latency.**
Handle: Celery jobs with status polling, an embedding cache, and a per-document FAISS index. The
upload call itself must return in under a second.

**8. "Where did this number come from?" is asked about every value.**
Handle: `provenance.py` is not optional. Enforce it at the DB level — a finding without an evidence
row should not be insertable.

---

## 10. What NOT to build

| Skip | Why |
|---|---|
| 10 government API integrations | 2 working beats 10 broken. Mock the rest. |
| Blockchain | No judge asks for it. It adds nothing to compliance verification. |
| Multi-agent AI orchestration | Fragile, slow, unexplainable. Fails live demos. |
| An AI chatbot | Not the problem statement. Pure distraction. |
| Custom ML model training | No time, no labelled data, no advantage. |
| Microservices / Kubernetes | Docker Compose is enough for a hackathon. |
| Heavy RAG infrastructure | FAISS files on disk are sufficient at this scale. |
| Fancy animations | Judges want proof, not motion. |

---

## 11. Demo script (5 minutes)

1. **0:00** — The problem in one line: manual bid verification takes days per tender and errors are costly.
2. **0:30** — Upload a real tender PDF. Show 27 requirements extracted, each with a page reference.
3. **1:30** — Upload the vendor bid. Show the claimed facts, each with its source snippet.
4. **2:15** — Run verification. Show the GST / Udyam records being fetched and cached.
5. **3:00** — **The moment:** the compliance matrix. 24 PASS, 3 FAIL, risk score 68 (HIGH).
6. **3:30** — Click the turnover FAIL: the bid claims 6.2 Cr (page 12, highlighted), the GST record
   shows 4.1 Cr. Side by side, on screen.
7. **4:15** — Download the PDF report. Show the audit log.
8. **4:45** — Close: "80% less verification effort, and every decision is traceable."

Rehearse it twice. Run it once with the internet disconnected.

---

## 12. Getting started

### Option A — one command (Docker Compose)

```bash
cp backend/.env.example backend/.env
docker compose up
```

That's it — `migrate` and `ollama-pull` run once and gate `api`/`worker` until the schema is applied
and the model is pulled, so there's no separate manual migration or `ollama pull` step to remember.

API docs: `http://localhost:8000/docs` · Dashboard via nginx: `http://localhost` · Dashboard direct
(bypasses nginx, same result thanks to the Vite dev-server proxy): `http://localhost:5173`

The `scripts/*.py` demo-data helpers assume a sibling `backend/`/`data/` layout that only exists on
the host, not inside the `api` container's build context — run them from the host against the
compose stack's Postgres (published on `localhost:5432`) the same way Option B does in step 6 below,
or just use the Upload page directly with your own PDFs.

### Option B — native processes (no Docker)

Useful when Docker isn't available (see `CLAUDE.md` for this project's SQLite/native-Ollama fallback)
or when iterating on backend/frontend code without rebuilding images.

```bash
# 1. Configure
cp backend/.env.example backend/.env

# 2. Start infrastructure
docker compose up -d postgres redis ollama
docker exec -it tenderguard-ollama ollama pull llama3.1:8b   # one time, ~5 GB

# 3. Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 4. Worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info --pool=solo   # --pool=solo on Windows

# 5. Frontend (separate terminal)
cd frontend && npm install && npm run dev

# 6. Seed demo data
python scripts/seed_mock_portals.py
python scripts/load_sample_data.py
```

API docs: `http://localhost:8000/docs` · Dashboard: `http://localhost:5173`

**Windows notes:** install Tesseract from the UB-Mannheim build and add it to `PATH`;
Celery needs `--pool=solo`; use WSL2 as the Docker backend.

---

## 13. Definition of done for the prototype

- [ ] Tender PDF → structured requirements with page references
- [ ] Vendor bid → claimed facts with source snippets
- [ ] At least 2 real government verifications, plus a full mock mode
- [ ] Deterministic rule engine producing a compliance matrix
- [ ] Every finding clickable through to its evidence
- [ ] Weighted risk score with severity bands
- [ ] Downloadable PDF report
- [ ] Append-only audit trail
- [ ] The entire demo runs offline
