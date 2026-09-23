# TenderGuard — Master Project Blueprint

> **How to read this document.** Every claim is tagged:
> - **[CONFIRMED]** — verified by reading the actual code/config in this repo.
> - **[ASSUMPTION]** — my inference, reasonable but unverified. Correct me if wrong.
> - **[REQUIRED INFO]** — I genuinely don't know; listed in §26. I have not guessed.
>
> Sources read: `README.md`, `CLAUDE.md`, `docs/{api,architecture,rule_pack_spec,demo_script}.md`,
> `backend/app/**` (models, routes, config, services), `backend/rules/*.yaml`, `backend/tests/`,
> `frontend/src/**`, `docker-compose.yml`, `infra/nginx/nginx.conf`, and the two problem logs
> `problem.md` (frontend UI/UX) + `project.md` (deployment).

---

## 1. PROJECT OVERVIEW

| Field | Value |
|---|---|
| **Project name** | TenderGuard **[CONFIRMED]** |
| **Title** | AI Tender & Vendor Compliance Verification **[CONFIRMED]** |
| **Problem ID** | SIH26100 (Smart India Hackathon) **[CONFIRMED]** |
| **Category** | GovTech / Document AI / Compliance automation **[CONFIRMED]** |
| **Stage** | Working prototype — 86 backend tests passing, full pipeline runs end-to-end **[CONFIRMED]** |

### Explained simply (for a beginner)

A government officer receives a **tender document** (the rules: "you must have ₹5 crore turnover, a
valid GST registration, 3 years experience") and a pile of **vendor bids** (companies saying "we have
₹6.2 crore turnover, here's our GST number"). Today the officer reads both by hand and checks whether
each claim is true. It takes days per tender, and a missed lie means a contract goes to a company
that shouldn't have won it.

TenderGuard reads both PDFs automatically, pulls out the rules and the claims, **checks the claims
against actual government records** (GST portal, Udyam/MSME registry, debarment lists), and produces
a table: 24 requirements passed, 3 failed — and for each one, the exact page and sentence it came
from, plus the government record that contradicts it.

### Core details

- **Problem statement** — manual verification of vendor bids against tender eligibility criteria is
  slow (days per tender), error-prone, and unauditable; vendors can overstate turnover, experience,
  or MSME status with little chance of being caught. **[CONFIRMED — README §1]**
- **Target users** — government procurement/tender evaluation officers. **[CONFIRMED]** Secondary:
  audit/vigilance staff reviewing past decisions. **[ASSUMPTION]**
- **Main objective** — reduce verification effort while making every PASS/FAIL decision traceable to
  a source page and a government record.
- **Expected outcome** — README claims "80% less verification effort, every decision traceable."
  **[CONFIRMED as a stated goal; not measured — no benchmark exists in the repo]**
- **Real-world use case** — an officer uploads a tender + a bid, runs verification, reviews the
  compliance matrix, downloads a PDF report that becomes part of the procurement file.

### Existing solutions and their limits

| Existing approach | Limitation |
|---|---|
| Fully manual reading + portal lookups | Days per tender; inconsistent across officers; no audit trail beyond notes |
| e-Procurement portals (GeM, CPPP) | Handle *submission and workflow*, not *semantic verification* of claims against government records **[ASSUMPTION — not researched in-repo]** |
| Generic "upload PDF → ask ChatGPT" tools | The LLM both reads *and* decides. Non-deterministic, unciteable, hallucinates, and cannot be defended in a procurement audit |

### Our proposed solution & USP

**The golden rule: the LLM extracts, it never decides.** **[CONFIRMED — enforced across the codebase]**

Every PASS/FAIL/NEEDS_REVIEW verdict comes from `backend/app/services/rules/engine.py`, a pure
function with no LLM calls and no I/O — same input, same output, every time. The LLM's only job is
turning unstructured PDF text into structured fields, and even that is guarded.

The five things that make this different from a RAG chatbot:

1. **Deterministic rule engine** — verdicts from officer-editable YAML, not model output.
2. **Government cross-verification** — GST/Udyam/debarment adapters; `source_priority` puts
   `government` ahead of `document`, which is *how an inflated claim gets caught*.
3. **Hallucination guardrail** — `snippet_guard.py` rejects any extraction whose quoted snippet is
   not literally present in the page text.
4. **Evidence on every finding** — DB-enforced 1:1 `Finding`↔`Evidence`; no verdict without a page.
5. **Runs offline** — `VERIFICATION_MODE=mock` + local Ollama; the demo works with WiFi off.

---

## 2. PROBLEM ANALYSIS

### 2.1 Domain problems (what the product solves)

#### P1 — Manual claim verification is slow
- **Who:** procurement officers. **Why:** every claim needs a separate portal lookup.
- **Frequency:** every bid, every tender — continuous.
- **Consequence if unsolved:** days of officer time per tender; verification quietly gets skipped
  under deadline pressure.
- **Current handling:** read the PDF, type the GSTIN into the GST portal by hand.
- **Our solution:** `POST /bids/{id}/verification` → adapter registry hits GST/Udyam/debarment,
  caches per bid+portal with a TTL. **[CONFIRMED]**

#### P2 — Vendors overstate facts, and nobody cross-checks
- **Who:** the buying department (and honest competing vendors).
- **Why:** the bid document is self-reported; checking it is expensive.
- **Consequence:** contracts awarded on false eligibility.
- **Our solution:** `source_priority: [government, document]` in the rule pack — the engine resolves
  the fact from the government record first, so a claimed ₹6.2 Cr against a GST-recorded ₹4.1 Cr
  surfaces as a FAIL with both numbers side by side. **[CONFIRMED — `rules/engine.py`]**

#### P3 — "Where did this number come from?" is unanswerable
- **Consequence:** decisions can't survive audit or a vendor challenge.
- **Our solution:** `Evidence` (page, bbox, snippet, document SHA-256) is 1:1 with every `Finding`;
  `compliance/service.py` resolves a real page reference with ordered fallbacks so a finding can
  never be persisted without one. **[CONFIRMED]**

#### P4 — Scanned/poor-quality PDFs
- **Our solution:** pages under ~50 chars of embedded text fall back to OCR (OpenCV deskew/denoise +
  Tesseract), which sets `low_confidence` rather than silently trusting bad output. **[CONFIRMED]**

#### P5 — Chaotic units and formats ("Rs. 5,00,00,000", "5 Cr", "5L")
- **Our solution:** one normalization boundary (`normalizers.py` / `fact_normalization.py`); nothing
  downstream parses raw strings. **[CONFIRMED]**

#### P6 — LLM hallucination would be fatal in procurement
- **Our solution:** temp 0 + pinned seed, JSON schema validation with a repair loop
  (`llm/json_guard.py`), and `snippet_guard.py` rejecting non-verbatim snippets. **[CONFIRMED]**

#### P7 — Government portals are down, rate-limited, captcha'd
- **Our solution:** adapters degrade to `status=DOWN`, never a false PASS/FAIL; the finding becomes
  NEEDS_REVIEW. Mock mode from day one. **[CONFIRMED]**

#### P8 — Requirements are written in ambiguous legal language
- **Our solution:** fixed taxonomy (`turnover | experience | certification | registration |
  financial | technical | msme | debarment | manual_review`); anything unmapped goes to
  `manual_review` rather than being force-fitted. **[CONFIRMED — `models/requirement.py`]**

### 2.2 Engineering problems found in this repo

Two audits were run and **both have been fixed** in the working tree:

- `problem.md` — 12 frontend UI/UX issues. **All 12 implemented.** Stepper nav with locked states,
  persistent tender/vendor context bar, session reset, toast system, real proportional risk gauge,
  formatted verification results, evidence deep-linking by `ruleId`, dead `FindingRow` deleted,
  skeleton loaders + consistent busy labels, re-run confirmation, sticky table headers, icon+color.
- `project.md` — 9 deployment issues. **8 of 9 implemented** (#9 CI/CD was flagged as awareness-only,
  no fix specified). Added `frontend/Dockerfile`, `migrate` + `ollama-pull` one-shot gating services,
  fixed the nginx prefix-stripping bug, moved the frontend to a same-origin proxy, `.dockerignore`
  for both services, `client_max_body_size 50m`, README rewritten with a real one-command path.

### 2.3 Master problem→solution table

| Problem | Cause | Existing Solution | Limitation | Our Solution | Expected Result |
|---|---|---|---|---|---|
| Slow manual verification | Per-claim portal lookups | Officer + browser | Days/tender | Adapter registry + TTL cache | Verification in seconds |
| Vendor overstates turnover | Self-reported bid | Spot checks | Rarely caught | `source_priority: government` first | Mismatch surfaces as FAIL |
| Unauditable verdicts | Notes, not records | Paper file | Can't defend on challenge | `Evidence` 1:1 with `Finding` + append-only `AuditLog` | Every verdict traceable to page |
| Scanned PDFs unreadable | No text layer | Manual retyping | Slow, error-prone | PyMuPDF → OCR fallback + `low_confidence` flag | Scanned docs usable, uncertainty visible |
| LLM hallucination | Generative model | — (fatal in naive designs) | Invented facts | temp 0 + JSON guard + snippet guard | Non-verbatim extractions rejected |
| Portal downtime | External dependency | Retry manually | False verdicts | Degrade to `DOWN` → NEEDS_REVIEW | Never a false PASS/FAIL |
| Messy units | Human-written figures | Manual reading | Comparison bugs | Single normalization boundary | Typed values in the engine |
| Ambiguous legal text | Legal drafting | Officer judgment | Inconsistent | Fixed taxonomy + `manual_review` bucket | No silent force-fitting |
| Non-reproducible decisions | LLM in the decision path | — | Different answer per run | Pure-function rule engine | Same input → same output |

---

## 3. REQUIREMENTS

### 3.1 Functional requirements

| # | Feature | User | Input | Processing | Output | Depends on | Priority | Status |
|---|---|---|---|---|---|---|---|---|
| F1 | Tender upload | Officer | PDF, title, ref no, category | SHA-256 dedupe → ingestion (Celery or inline) | `{tender_id, document, job_id, duplicate}` | — | Must | ✅ **[CONFIRMED]** |
| F2 | Bid upload | Officer | PDF, tender_id, vendor name, GSTIN, PAN, MSME flag | Vendor reuse by GSTIN → dedupe → ingestion | `{bid_id, ...}` | F1 | Must | ✅ |
| F3 | PDF ingestion | System | PDF | PyMuPDF per-page text + word bboxes; OCR fallback <50 chars | `Document` + `DocumentPage` rows | — | Must | ✅ |
| F4 | Requirement extraction | System | Tender pages | Ollama temp 0 → JSON schema → snippet guard | `Requirement` rows w/ page + snippet | F3 | Must | ✅ |
| F5 | Claimed-fact extraction | System | Bid pages | Same pipeline, different prompt | `ClaimedFact` rows | F3 | Must | ✅ |
| F6 | Government verification | Officer | bid_id | GST/Udyam/debarment adapters, mock or live, TTL-cached | `VerificationResult` rows | F2 | Must | ✅ |
| F7 | Rule evaluation | Officer | bid_id | Load YAML pack for category → pure-function engine | `Finding` + `Evidence` rows | F4-F6 | Must | ✅ |
| F8 | Risk scoring | System | Findings | Weighted 0-100; FAILed BLOCKER forces HIGH | score + band + counts | F7 | Must | ✅ |
| F9 | Compliance matrix UI | Officer | — | Fetch + filter by status | Table, clickable rows | F7 | Must | ✅ |
| F10 | Evidence viewer | Officer | rule id | Claimed vs verified side by side + snippet | Evidence page | F7 | Must | ✅ |
| F11 | PDF report | Officer | bid_id | ReportLab: summary + matrix + evidence appendix + hashes | `application/pdf` stream | F7 | Must | ✅ |
| F12 | Audit trail | System | every action | Append-only insert | `AuditLog` rows; `GET /audit` | — | Must | ✅ |
| F13 | Semantic clause search | Officer | tender_id, query | FAISS + sentence-transformers over tender chunks | Top-5 clauses | F3 | Should | ✅ (undocumented — see §14) |
| F14 | Requirements review page | Officer | tender_id | List extracted requirements | Table | F4 | Should | ⚠️ Read-only; `human_reviewed` flag exists but **no UI to set it** |
| F15 | Officer authentication | Officer | credentials | — | — | — | Must for production | ❌ **Not built** — `X-Actor` header, default `"officer"` |
| F16 | Multi-bid comparison | Officer | tender_id | Rank bids for one tender | Comparison view | F7 | Nice | ❌ Not built |

### 3.2 Non-functional requirements

| Area | Requirement | Priority | Current state |
|---|---|---|---|
| Performance | Upload returns <1s (ingestion async) | Must | ✅ `enqueue.py` probes Redis, falls back inline **[CONFIRMED]** |
| Determinism | Same document → same verdict | Must | ✅ Pure engine, temp 0, pinned seed |
| Reliability | Portal failure never yields false PASS/FAIL | Must | ✅ Degrades to `DOWN` |
| Availability | Full demo runs offline | Must | ✅ Mock mode + local Ollama |
| Security | AuthN/AuthZ | Must (prod) | ❌ **None** — see §13 |
| Security | Upload validation | Must | ⚠️ Partial — `MAX_UPLOAD_MB=50`, nginx 50m; **content-type/magic-byte check unverified** |
| Data privacy | Bid documents are commercially sensitive | Must | ⚠️ No encryption at rest, no access control |
| Maintainability | Rules editable without code changes | Must | ✅ YAML packs, no `eval()` |
| Usability | Officer can follow the pipeline unaided | Should | ✅ Stepper nav + context bar (post-`problem.md` fixes) |
| Accessibility | Status never conveyed by color alone | Should | ✅ Chips and risk band pair color with text+icon |
| Error handling | Uniform envelope | Must | ✅ `{code, message, detail}` via `core/errors.py` |
| Logging | Structured, request-scoped | Should | ✅ `structlog` in `core/logging.py` |
| Testing | Core logic covered | Must | ✅ 86 tests **[CONFIRMED]**; ❌ 0 frontend tests |
| Monitoring | Health + metrics | Should | ⚠️ `GET /health` only; no metrics/alerting |
| Backup | DB + uploaded documents | Should | ❌ None defined |
| Scalability | Concurrent officers | Nice | ⚠️ Untested; Celery exists but Windows needs `--pool=solo` |

---

## 4. USER ROLES

**[CONFIRMED]** The system today has **exactly one implicit role** and no authentication. The
`X-Actor` header names the actor for audit purposes and defaults to `"officer"`; nothing verifies it.

Proposed role model for production **[ASSUMPTION — needs confirmation, see §26]**:

| Role | Responsibilities | Key permissions |
|---|---|---|
| **Officer** (exists today) | Upload, verify, run compliance, review, download report | Full CRUD on own tenders/bids |
| **Reviewer / Senior officer** | Approve or override NEEDS_REVIEW findings | Read all; set `human_reviewed`; add override with justification |
| **Auditor / Vigilance** | Post-hoc review | Read-only everything incl. full audit log; no mutations |
| **Admin** | Manage users, edit rule packs | User CRUD; rule pack upload/versioning |

### Role–permission matrix (proposed)

| Action | Officer | Reviewer | Auditor | Admin |
|---|:--:|:--:|:--:|:--:|
| Upload tender/bid | ✅ | ✅ | ❌ | ✅ |
| Run verification | ✅ | ✅ | ❌ | ✅ |
| Run/re-run compliance | ✅ | ✅ | ❌ | ✅ |
| View compliance matrix | ✅ (own) | ✅ (all) | ✅ (all) | ✅ |
| Mark requirement reviewed | ❌ | ✅ | ❌ | ✅ |
| Override a finding | ❌ | ✅ (logged) | ❌ | ✅ |
| Download report | ✅ | ✅ | ✅ | ✅ |
| Read audit log | own | ✅ | ✅ | ✅ |
| Edit rule packs | ❌ | ❌ | ❌ | ✅ |
| Manage users | ❌ | ❌ | ❌ | ✅ |

> **Note the contradiction to resolve:** the "officer review step before the rule engine runs" that
> README §9 lists as a hallucination countermeasure **is not implemented** — `human_reviewed` exists
> as a column with no UI to set it (F14). Either build it or stop claiming it.

---

## 5. COMPLETE SYSTEM WORKFLOW

### 5.1 Main flow — upload to verdict **[CONFIRMED end-to-end]**

```
Officer
  ↓  selects tender PDF + metadata
Frontend (React, Upload page)
  ↓  POST /api/v1/tenders  (multipart)
Vite proxy / nginx  →  FastAPI
  ↓
save_upload() → SHA-256 → duplicate? → Document row (status=pending)
  ↓
enqueue.py: is Redis reachable?
  ├── yes → Celery task  ──┐
  └── no  → run inline  ───┤   (upload always completes)
                           ↓
Ingestion: PyMuPDF per-page text + word bboxes
   page <50 chars? → OCR (OpenCV deskew/denoise + Tesseract) → low_confidence flag
                           ↓
              DocumentPage rows + FAISS index built
                           ↓
Extraction: Ollama (temp 0, seed pinned), per page
   → JSON forced + Pydantic schema + repair loop (json_guard.py)
   → snippet_guard.py: is the quoted snippet literally in the page text?
        NO → REJECT the extraction (hallucination guardrail)
        YES ↓
   → normalizers.py: "Rs. 5,00,00,000" → {value: 50000000, unit: INR}
                           ↓
        Requirement rows (tender) / ClaimedFact rows (bid)
                           ↓
Officer clicks "Run verification"  →  POST /bids/{id}/verification
                           ↓
   registry.py → mock (data/mock_portals/*.json) or live adapters
   live adapter unreachable → status=DOWN  (never a false PASS/FAIL)
   → VerificationResult rows, cached per bid+portal with TTL
                           ↓
Officer clicks "Run compliance"  →  POST /bids/{id}/compliance
                           ↓
   compliance/service.py builds claimed{} / verified{} / context{}
                           ↓
   rules/loader.py loads backend/rules/default_<category>.yaml
                           ↓
   rules/engine.py  ── PURE FUNCTION, NO LLM, NO I/O ──
     for each rule:
       applies_if? → condition.py (fixed grammar, never eval())  → skip if false
       resolve fact via source_priority  (government beats document)
       evaluate with operators.py  (gte/lte/gt/lt/eq/in/regex/date_*/exists)
       → PASS | FAIL | NEEDS_REVIEW + reason
                           ↓
   risk/scorer.py: weighted 0-100; FAILed BLOCKER forces HIGH band
                           ↓
   Finding rows REPLACED (not appended) + 1 Evidence row each
   (page fallback chain: bid page → tender page → page 1)
                           ↓
   audit/trail.py appends a row (actor from X-Actor)
                           ↓
Response {risk, findings}  →  Frontend
                           ↓
Compliance matrix: risk gauge, PASS/FAIL/REVIEW counts, filterable table
                           ↓
Officer clicks a row  →  /evidence/:ruleId
   claimed vs government-verified side by side, snippet, page, SHA-256
                           ↓
Officer downloads report  →  GET /bids/{id}/report
   ReportLab: summary + matrix + evidence appendix + both document hashes
```

### 5.2 Sub-flows

- **Authentication flow** — ❌ **does not exist.** `X-Actor` header is trusted verbatim.
- **Authorization flow** — ❌ does not exist. Any caller can read any bid by UUID.
- **File upload flow** — multipart → `save_upload()` → SHA-256 → dedupe → disk (`UPLOAD_DIR`) →
  `Document` row → enqueue. **[CONFIRMED]**
- **Error flow** — `AppError(code, message, status_code, detail)` → global handler → uniform
  `{code, message, detail}` envelope. Frontend shows inline message **and** a toast. **[CONFIRMED]**
- **AI flow** — see §12. Extraction only; never decisions.
- **Notification flow** — in-app toasts only (frontend `ToastContext`). No email/SMS/push.
- **Admin flow** — ❌ none. Rule packs are edited as files on disk.
- **Session flow (frontend)** — `tenderId`/`bidId` in `SessionContext`, persisted to `localStorage`
  under `tenderguard.session`; reset via "Start new session" in the nav context bar. **[CONFIRMED]**

---

## 6. SYSTEM ARCHITECTURE

### 6.1 High-level

```
                      Officer's browser
                             │
                             ▼
                  nginx  (port 80, single ingress)
                   ├── /        → frontend (Vite dev server / built dist)
                   └── /api/    → api:8000    [client_max_body_size 50m]
                             │
                             ▼
                  FastAPI  (app/api/v1/routes/*)
                   health · tenders · bids · verification · compliance · reports · audit
                             │
                             ▼
                  Business logic (app/services/*)
   ┌──────────┬──────────┬──────────┬──────────┬──────────┬─────────┐
   ▼          ▼          ▼          ▼          ▼          ▼         ▼
ingestion  extraction  retrieval  verification  rules     risk   compliance
PyMuPDF    Ollama      FAISS +    GST/Udyam/    YAML      0-100   glue +
+ OCR      + guards    ST embeds  debarment     engine    +band   persistence
   │          │          │          │            │          │         │
   └──────────┴──────────┴────┬─────┴────────────┴──────────┴─────────┘
                              ▼
        PostgreSQL (prod)  /  SQLite (this machine)      Redis + Celery
        11 tables, append-only AuditLog                  async ingestion
                              │
                              ▼
                  reports (ReportLab PDF)  ·  audit trail
```

### 6.2 Why each component

| Component | Why it's required |
|---|---|
| **nginx** | Single ingress on :80; sets the 50MB body limit that real tender PDFs need |
| **FastAPI** | Async, native Pydantic validation, free OpenAPI docs (judges can poke `/docs`) |
| **PostgreSQL** | Relational integrity for the `Finding`→`Evidence` 1:1 invariant; JSON columns for flexible fact dicts |
| **SQLite fallback** | Postgres installer blocked on this network; models use dialect-generic `Uuid`/`JSON` so only `DATABASE_URL` changes **[CONFIRMED — CLAUDE.md]** |
| **Redis + Celery** | Long PDFs would block the request; upload must return <1s. Degrades to inline when absent |
| **Ollama (local LLM)** | Offline demo requirement + data sensitivity — bid documents never leave the machine |
| **FAISS + sentence-transformers** | Semantic clause search ("find the clause about turnover") without a vector DB service |
| **PyMuPDF + Tesseract** | Text layer when present, OCR when not; word bboxes enable evidence highlighting |
| **YAML rule packs** | Rules are officer-editable data, not code — the core auditability claim |
| **ReportLab** | The PDF report is the officer's actual deliverable into the procurement file |

---

## 7. TECHNOLOGY STACK

**All versions below are [CONFIRMED] from `requirements.txt` / `package.json`.**

### Frontend
| Concern | Choice | Why | Alternative |
|---|---|---|---|
| Framework | React 19.2 | Team familiarity, largest ecosystem | Vue, Svelte |
| Build | Vite 8.2 | Instant HMR; dev-server proxy solves same-origin API cleanly | Next.js (SSR unnecessary here) |
| CSS | Tailwind 4.3 | Fast iteration, no naming overhead | CSS Modules |
| Routing | react-router-dom 7.18 | Standard; supports the `/evidence/:ruleId` deep link | TanStack Router |
| API client | axios 1.20 | Interceptors, multipart | fetch + wrapper |
| State | React Context (`SessionContext`, `ToastContext`) | App state is tiny — 2 IDs + toasts | Zustand/Redux (overkill) |
| Lint | oxlint 1.79 | Very fast | ESLint |
| Form validation | ❌ **none** — manual `disabled` checks | — | react-hook-form + zod **(recommended)** |

### Backend
| Concern | Choice | Why | Alternative |
|---|---|---|---|
| Language | Python 3.12 | The PDF/OCR/ML ecosystem lives here | — |
| Framework | FastAPI 0.141 | Async + Pydantic + OpenAPI | Django REST (heavier) |
| API style | REST `/api/v1` | Simple, demoable | GraphQL (no benefit here) |
| ORM | SQLAlchemy 2.0 (typed `Mapped[]`) | Dialect-generic types → Postgres/SQLite portability | SQLModel |
| Migrations | Alembic 1.19 | Standard | — |
| Validation | Pydantic 2.13 | Shared with LLM output schemas | — |
| Logging | structlog 26.1 | Structured + request IDs | stdlib logging |
| Auth | ❌ **none** | — | **fastapi-users / JWT (required for prod)** |

### Database
- **Postgres 16** (docker) / **SQLite** (this machine). 11 tables — see §8.
- Dialect-generic `Uuid(as_uuid=True)` and `JSON` throughout — **never** `postgresql.UUID`/`JSONB`.
  **Keep it that way when adding models.** **[CONFIRMED — CLAUDE.md constraint]**

### AI
| Concern | Choice | Notes |
|---|---|---|
| LLM runtime | Ollama, temp 0, pinned seed | Offline + deterministic |
| Model | `llama3.1:8b` (documented) / `qwen2.5:3b` (this machine) | ⚠️ **contradiction — see §14** |
| Embeddings | sentence-transformers 6.0 | Local |
| Vector store | faiss-cpu 1.15, on-disk per document | No service to run |
| Chunking | `retrieval/chunker.py` | Layout-aware (headings/tables) |
| OCR | pytesseract + opencv-headless | Deskew/denoise before OCR |
| PDF | PyMuPDF 1.28 + pdfplumber | Word-level bboxes for evidence |
| Guardrails | `json_guard.py`, `snippet_guard.py` | Schema repair loop + verbatim check |
| Agents / tool-calling | ❌ deliberately **not** used | README §10: "fragile, slow, unexplainable" |

### DevOps
Git; Docker Compose (postgres, redis, ollama, ollama-pull, migrate, api, worker, frontend, nginx);
❌ no CI/CD; ❌ no hosted deployment target.

---

## 8. DATABASE DESIGN

**11 tables [CONFIRMED].** All inherit `UUIDPKMixin` (`id: UUID pk, default uuid4`); most also
inherit `TimestampMixin` (`created_at`, `updated_at` server-side). `AuditLog` deliberately omits
`TimestampMixin` — it has its own immutable `timestamp` and is never updated.

```
Document ──1:N── DocumentPage
   │
   ├──1:1── Tender ──1:N── Requirement
   │            │                 ▲
   │            └──1:N── Bid      │ (external_ref == rule.id)
   │                      │       │
   └──1:1─────────────────┤       │
                          ├──1:N── ClaimedFact
Vendor ──1:N── Bid ───────┼──1:N── VerificationResult
                          └──1:N── Finding ──1:1── Evidence ──→ Document

AuditLog  (standalone, append-only, no FKs — survives entity deletion)
```

| Table | Purpose | Key fields | Notes |
|---|---|---|---|
| `documents` | Uploaded PDF | `kind` (TENDER/BID enum), `filename`, `storage_path`, **`sha256` UNIQUE idx**, `page_count`, `status` | SHA-256 uniqueness *is* the dedupe mechanism |
| `document_pages` | Per-page text + layout | `document_id` idx, `page_number`, `text`, `ocr_used`, `ocr_confidence`, `low_confidence`, `layout` JSON | `layout` = `[{text, bbox}]` for highlighting |
| `tenders` | Tender | `title`, `reference_no`, `document_id`, **`category`** | `category` selects the rule pack |
| `requirements` | Eligibility criterion | `tender_id` idx, `external_ref`, `text`, `category` (taxonomy), `expected` JSON, `source_page`, `source_snippet`, `human_reviewed` | `external_ref` links to `rule.id` |
| `vendors` | Company | `name`, `gstin` idx, `pan` idx, `udyam_number` idx | Reused across bids by GSTIN |
| `bids` | One vendor's bid | `vendor_id` idx, `tender_id` idx, `document_id`, `claims_msme_benefit` | Cascade delete from both parents |
| `claimed_facts` | LLM-extracted claim | `bid_id` idx, `fact_key` idx (dotted path), `raw_value`, `normalized_value` JSON, `source_page`, `source_snippet` | `raw_value` kept verbatim for audit |
| `verification_results` | Portal response | `bid_id` idx, `portal`, `status` (UP/DOWN/NOT_FOUND), `normalized` JSON, `raw_response` JSON, `fetched_at` | `fetched_at` drives TTL |
| `findings` | One verdict | `bid_id` idx, `requirement_id` idx, `rule_id`, `weight`, `expected`/`claimed`/`verified` JSON, `status`, `reason`, `severity`, `risk_contribution` | Replaced wholesale on re-run |
| `evidence` | Provenance | `finding_id` **UNIQUE** idx, `document_id`, `page_number`, `bbox` JSON, `snippet`, `document_sha256` | UNIQUE enforces 1:1 |
| `audit_logs` | Append-only trail | `actor`, `action`, `entity_type`, `entity_id`, `before`/`after` JSON, `timestamp` | Insert-only by convention |

### Indexing strategy **[CONFIRMED where marked idx]**
Present: every FK, `documents.sha256` (unique), vendor identifiers, `claimed_facts.fact_key`,
`evidence.finding_id` (unique). **Recommended additions [ASSUMPTION]:** composite
`(bid_id, portal)` on `verification_results` (the cache's lookup pattern) and
`(entity_type, entity_id, timestamp)` on `audit_logs` (the `/audit` filter pattern).

### Validation, backup, integrity
- Validation at the API boundary (Pydantic) and the normalization boundary. `Evidence` 1:1 is the
  one DB-level business invariant.
- **Backup: ❌ not defined.** For production you need both the DB *and* `data/uploads/` — a finding's
  SHA-256 is worthless if the source PDF is gone.

---

## 9. API DESIGN

Base: `/api/v1`. All errors: `{code, message, detail}`. Auth: **none** (`X-Actor` header, default
`"officer"`). Interactive docs at `/docs`.

### Health
```
GET /health → 200 always
{"status":"ok","service":"tenderguard-api","dependencies":{"database":"up"}}
```
Never hangs or raises even if the DB is down. **[CONFIRMED — tested live]**

### Tenders
```
POST /tenders            multipart: file, title, reference_no?, category?(goods|works|services)
  → 201 {tender_id, document, job_id, duplicate}
GET  /tenders/{id}                → tender + document status
GET  /tenders/{id}/pages          → [{page_number, char_count, ocr_used, ocr_confidence, preview}]
GET  /tenders/{id}/requirements   → [Requirement]
GET  /tenders/{id}/search?q=...   → top-5 semantic clause matches   ⚠️ UNDOCUMENTED in docs/api.md
```

### Bids
```
POST /bids   multipart: file, tender_id, vendor_name, gstin?, pan?, udyam_number?, claims_msme_benefit?
  → 201 {bid_id, ...}       (reuses an existing vendor when GSTIN matches)
GET  /bids/{id}            → bid + vendor + claimed facts
GET  /bids/{id}/pages      → same shape as tender pages
```

### Verification
```
POST /bids/{id}/verification → {results:[{portal, status, normalized, raw_response, fetched_at}]}
GET  /bids/{id}/verification → cached results, most recent first
```

### Compliance
```
POST /bids/{id}/compliance → {risk, findings}   ⚠️ DESTRUCTIVE: replaces prior findings
GET  /bids/{id}/compliance → persisted findings, risk recomputed (no re-run); 404 if never run

finding: {rule_id, requirement_text, expected, claimed, verified, status, reason,
          severity, risk_contribution,
          evidence:{document_id, page_number, bbox, snippet, document_sha256}}
risk:    {score 0-100, band LOW|MEDIUM|HIGH, pass_count, fail_count, needs_review_count}
```

### Reports
```
GET /bids/{id}/report → application/pdf, Content-Disposition: attachment
```

### Audit
```
GET /audit?entity_type=&entity_id=&limit=100  (capped at 500) → [AuditLog]
```

### Missing endpoints for the roadmap **[ASSUMPTION]**
`POST /auth/login`, `GET /tenders` (list), `GET /bids` (list), `PATCH /requirements/{id}`
(the `human_reviewed` review step), `POST /findings/{id}/override`, `GET /tenders/{id}/bids/compare`.

---

## 10. FRONTEND STRUCTURE

### Actual structure **[CONFIRMED]**
```
frontend/src/
├── App.jsx                       # SessionProvider > ToastProvider > NavBar > Routes
├── main.jsx
├── index.css
├── api/
│   └── client.js                 # axios; baseURL '' → same-origin /api/v1 via proxy/nginx
├── store/
│   ├── SessionContext.jsx        # {tenderId, bidId, tenderTitle, vendorName, update, reset}
│   └── ToastContext.jsx          # notify(msg, {type:'success'|'error'}) + auto-dismiss
├── components/
│   ├── common/
│   │   ├── NavBar.jsx            # 5-step stepper, locked states, context bar, session reset
│   │   ├── ApiStatus.jsx         # health probe + DB status
│   │   └── icons.jsx             # Check / Warning / Alert / Lock
│   └── compliance/
│       ├── RiskGauge.jsx         # proportional gradient bar + band marker + icon
│       └── StatusChip.jsx        # PASS / FAIL / NEEDS_REVIEW, color + text
└── pages/
    ├── Upload.jsx                # two gated forms: tender → bid
    ├── Requirements.jsx          # extracted requirements table
    ├── ComplianceMatrix.jsx      # risk gauge, counts, filters, findings table
    ├── EvidenceViewer.jsx        # claimed vs verified, snippet, page, hash
    └── Reports.jsx               # PDF download
```

### Routing
```
/                 Upload            always available
/requirements     Requirements      needs tenderId
/compliance       ComplianceMatrix  needs bidId
/evidence         EvidenceViewer    empty state
/evidence/:ruleId EvidenceViewer    deep-linkable; refetches if router state is missing
/reports          Reports           needs bidId
```

**Protected routes:** ❌ no auth guards. Gating is *pipeline-state* only (nav steps lock until the
prerequisite ID exists) — a usability affordance, **not** a security control.

**State conventions [CONFIRMED]:** loading → skeleton placeholders (no layout shift); error → inline
message + toast; empty → explicit copy with a link to the prerequisite step; busy → in-button labels
("Uploading…", "Verifying…", "Running…"); destructive → `confirm()` before re-running compliance.

**Gaps:** no form-validation library (manual `disabled` logic); no frontend tests; responsive
strategy is sticky headers + horizontal scroll, no mobile card layout.

---

## 11. BACKEND STRUCTURE

```
backend/
├── app/
│   ├── main.py               # FastAPI app, CORS, error handlers, 7 routers @ /api/v1
│   ├── config.py             # Settings; PROJECT_ROOT anchoring for .env + data dirs
│   ├── api/v1/routes/        # HTTP only — parse, delegate, serialize. No business logic.
│   │   ├── health.py tenders.py bids.py verification.py compliance.py reports.py audit.py
│   ├── core/
│   │   ├── deps.py           # get_db session dependency
│   │   ├── errors.py         # AppError + global handlers → {code,message,detail}
│   │   └── logging.py        # structlog, request ids
│   ├── db/
│   │   ├── base.py session.py
│   │   └── migrations/       # alembic (env.py uses resolved_database_url)
│   ├── models/               # 11 SQLAlchemy models + mixins
│   ├── schemas/              # Pydantic request/response DTOs
│   ├── services/             # ALL business logic lives here
│   │   ├── ingestion/        # pdf_loader, ocr, layout, pipeline, upload, enqueue
│   │   ├── extraction/       # requirement/fact extraction, normalizers, snippet_guard
│   │   ├── llm/              # ollama client, json_guard, prompts/*.txt
│   │   ├── retrieval/        # chunker, embeddings, vector_store, search (FAISS)
│   │   ├── verification/     # registry, cache, adapters/{gst,udyam,mock_portal}
│   │   ├── rules/            # loader, engine, operators, condition   ← NO LLM, NO I/O
│   │   ├── risk/             # scorer
│   │   ├── compliance/       # service (glue), requirement_binding
│   │   ├── reports/          # pdf_builder (ReportLab)
│   │   └── audit/            # trail
│   └── workers/              # celery_app, tasks
├── rules/                    # default_goods.yaml, default_works.yaml, default_services.yaml
├── tests/                    # 86 tests
├── Dockerfile  .dockerignore  requirements.txt  .env.example  alembic.ini
```

**Folder responsibilities:** routes are thin (HTTP concerns only); `services/` holds all logic and is
independently testable; `models/` is persistence-only; `schemas/` is the wire contract; `core/` is
cross-cutting. **The architectural rule: nothing in `rules/`, `risk/`, or `compliance/` may import
the LLM layer.** **[CONFIRMED — CLAUDE.md hard constraint]**

---

## 12. AI / ML ARCHITECTURE

### Where AI is and isn't used **[CONFIRMED]**

| Task | AI? | Why |
|---|:--:|---|
| Extract requirements from tender text | ✅ | Unstructured legal prose → structured fields |
| Extract claimed facts from bid text | ✅ | Same |
| Semantic clause search | ✅ | Embeddings beat keyword search for "the turnover clause" |
| **Deciding PASS/FAIL** | ❌ | **Must be deterministic, explainable, auditable** |
| Risk scoring | ❌ | Weighted arithmetic over rule weights |
| Verification | ❌ | Government API responses are facts, not inferences |
| Report generation | ❌ | Templated |

### Pipeline

```
Page text
   ↓
Prompt (prompts/requirement_extraction.txt | vendor_fact_extraction.txt)
   ↓
Ollama — temperature 0, seed pinned, JSON mode
   ↓
json_guard.py — parse + Pydantic validate; on failure, repair loop
   ↓
snippet_guard.py — is the quoted snippet LITERALLY in the page text?
   ├── NO  → REJECT  ◀── the hallucination guardrail
   └── YES ↓
normalizers.py — "Rs. 5,00,00,000" | "5 Cr" | "5L" → {value:50000000, unit:"INR"}
   ↓
Requirement / ClaimedFact rows (each with page + verbatim snippet)
   ↓
════════ AI BOUNDARY — nothing below this line calls an LLM ════════
   ↓
rules/engine.py (pure) → risk/scorer.py → Finding + Evidence
```

### RAG specifics
Chunking is layout-aware (`retrieval/chunker.py` uses detected headings/tables); embeddings via
sentence-transformers; per-document FAISS index on disk under `VECTORSTORE_DIR`; `search.py` returns
top-5. Used for `GET /tenders/{id}/search`, **not** in the verdict path.

### Hallucination prevention — four independent layers
1. Temperature 0 + pinned seed → reproducible.
2. Forced JSON + schema validation + repair loop → structurally valid.
3. **Snippet guard** → every extracted value is traceable to literal source text.
4. **The LLM never decides** → even a bad extraction produces a *reviewable finding*, not a verdict.

### Evaluation & confidence — ⚠️ gaps
- OCR confidence is captured (`ocr_confidence`, `low_confidence`); **extraction confidence is not
  scored**, and there is **no evaluation harness** measuring extraction accuracy against a labelled
  set. Rejections are silent — worth surfacing "N extractions rejected by snippet guard" in the UI.
- Human verification: `human_reviewed` exists but has **no UI** (see F14).

---

## 13. SECURITY

> **Overall posture: appropriate for a local hackathon demo; NOT deployable to a real procurement
> environment without §13.1.** Bid documents are commercially sensitive and legally privileged.

### 13.1 Critical — must fix before any real deployment

| # | Risk | Cause | Solution | Implementation |
|---|---|---|---|---|
| S1 | **No authentication.** Anyone reaching the API is "officer" | Never built; `X-Actor` header trusted verbatim | JWT or session auth | `fastapi-users` or hand-rolled OAuth2PasswordBearer + `users` table; make `get_current_user` a dependency on every non-health route |
| S2 | **No authorization.** Any caller can read any bid by UUID (IDOR) | No ownership model | Per-resource ownership checks | Add `owner_id` to `tenders`/`bids`; filter every query by the authenticated user's scope |
| S3 | **Audit trail is forgeable.** `X-Actor` is attacker-controlled | Header trusted as identity | Derive actor from the verified session, never the header | One-line change in `audit/trail.py` once S1 lands — **the entire audit claim depends on this** |
| S4 | **Documents unprotected at rest.** PDFs on disk, world-readable to the process | No encryption/ACL | Encrypt at rest or restrict to an object store with signed URLs | Minimum: OS-level permissions on `UPLOAD_DIR` + never serve raw paths |
| S5 | **Report endpoint is unauthenticated.** `GET /bids/{id}/report` streams a full compliance PDF to any caller with the UUID | Same as S2 | Gate behind auth + ownership | Guess-resistant UUIDs help but are **not** access control |

### 13.2 Important

| # | Risk | Status | Fix |
|---|---|---|---|
| S6 | Upload content validation | ⚠️ Size capped (50MB app + nginx); **magic-byte/content-type verification unverified** | Verify `%PDF` header; reject mismatched content-type; consider AV scan |
| S7 | Zip-bomb / malicious PDF | ⚠️ PyMuPDF/Tesseract parse untrusted input | Page-count ceiling, per-document processing timeout, run ingestion in a resource-capped worker |
| S8 | No rate limiting | ❌ Absent everywhere | `slowapi` on uploads and compliance runs (both expensive) |
| S9 | CORS | ✅ Explicit allowlist via `CORS_ORIGINS`, not `*` | Keep; tighten per environment |
| S10 | Secrets management | ⚠️ `.env` files; **correctly gitignored — verified no `.env` is tracked** | Use a secret manager in prod; rotate the compose Postgres password (`tenderguard:tenderguard`) |
| S11 | SQL injection | ✅ SQLAlchemy ORM throughout, no raw SQL seen | Keep; never f-string a query |
| S12 | `eval()` in rule conditions | ✅ **Deliberately avoided** — `condition.py` uses a fixed grammar | This is exactly right; never "simplify" it to `eval()` |
| S13 | XSS | ✅ React escapes by default; no `dangerouslySetInnerHTML` found | Keep |
| S14 | CSRF | N/A today (no cookie auth) | Becomes relevant the moment S1 uses cookies — prefer `Authorization` header tokens |
| S15 | Sensitive data in logs | ⚠️ Unaudited — `raw_response` JSON may hold PII from portals | Add a redaction filter to structlog |
| S16 | Password hashing | N/A (no passwords yet) | argon2/bcrypt when S1 lands — never SHA-256 |

---

## 14. ERROR ANALYSIS

### 14.1 Resolved this session

| Error | Cause | Location | Solution | Prevention |
|---|---|---|---|---|
| `docker compose up` fails instantly | `frontend` service referenced a non-existent Dockerfile | `docker-compose.yml` | Added `frontend/Dockerfile` | CI that runs `docker compose build` |
| API on empty schema | No migration step in the Docker path | `docker-compose.yml` | One-shot `migrate` service, gated via `service_completed_successfully` | Same CI |
| All nginx `/api/` calls 404 | Trailing slash on `proxy_pass` stripped the `/api` prefix every route needs | `infra/nginx/nginx.conf` | Removed trailing slash | A smoke test through :80, not just :8000 |
| nginx path never exercised | Frontend called `:8000` directly, bypassing nginx | compose + `client.js` | Same-origin relative base + Vite proxy | Route the demo through :80 |
| 413 on real tender PDFs | nginx default 1MB vs app's 50MB | nginx.conf | `client_max_body_size 50m` | Test with a realistic 10MB+ PDF |
| Multi-GB build context | No `.dockerignore`; `backend/.venv` is 1.5GB | backend/, frontend/ | Added both | — |
| First extraction fails after deploy | Model pull was a manual step | compose | `ollama-pull` one-shot + healthcheck gate | — |
| Evidence page blank on refresh | Finding read only from in-memory router state | `EvidenceViewer.jsx` | Route by `:ruleId`, refetch on mount | — |
| Dead `FindingRow` diverged from the live table | Half-finished refactor | components/compliance | Deleted | Lint rule for unused files |

### 14.2 Open contradictions — **these need your decision**

| # | Contradiction | Detail |
|---|---|---|
| C1 | **`docs/api.md` says "There's no dedicated `/audit` list endpoint yet"** — but `routes/audit.py` implements `GET /audit` with filtering and is registered in `main.py` | Doc is stale. Fix the doc. |
| C2 | **`GET /tenders/{id}/search` exists but is undocumented** in `docs/api.md` | Semantic clause search — a genuinely demo-worthy feature that's invisible in the docs *and* unreachable from the UI |
| C3 | **Model mismatch** — README/`.env.example` say `llama3.1:8b`; `backend/.env` uses `qwen2.5:3b` | Deliberate (3B fits this machine), but extraction quality and the demo differ from what's documented. Decide which is canonical before judging. |
| C4 | **README §9 claims "an officer review step before the rule engine runs"** as a hallucination countermeasure | Not implemented — `human_reviewed` has no UI. Either build it or drop the claim. |
| C5 | **`CLAUDE.md` calls Docker Compose "the intended one-command path"**, but Docker isn't installed on this machine | Compose fixes are correct by inspection but **have never actually been run**. See §26. |
| C6 | **`frontend/.env` now pins `VITE_API_BASE_URL=http://localhost:8001`** while all docs say `:8000` | Both ports currently respond, so this is presumably deliberate — but it overrides the same-origin proxy the deployment fixes introduced, so nginx is bypassed again in local dev |

### 14.3 Predicted future errors

| Likely error | Trigger | Prevention |
|---|---|---|
| Celery worker hangs on Windows | `--pool=solo` omitted | Documented; enforce in a start script |
| Extraction returns `{}` for scanned docs | OCR quality below the model's threshold | Surface `low_confidence` prominently; already flagged in the data |
| Rule pack YAML typo breaks compliance | Officer edits the pack | Already mitigated — line-tracking loader fails fast with a line number |
| Timezone comparison bug on Postgres | Cache compares naive vs aware datetimes | Already handled for SQLite; **re-verify when switching to Postgres** |
| FAISS index missing after re-upload | Dedupe skips re-ingestion | Verify index existence independently of document status |
| Report PDF fails on very long matrices | ReportLab pagination | Test with a 50-rule pack |

---

## 15. EDGE CASES

| Scenario | Expected behavior | Implementation status |
|---|---|---|
| Empty/0-byte PDF | Reject with a clear message | ⚠️ **Unverified** |
| Non-PDF renamed to `.pdf` | Reject on magic bytes | ⚠️ **Unverified — likely a gap** |
| Password-protected PDF | Fail gracefully with a specific error | ⚠️ **Unverified** |
| >50MB upload | 413 with a clear message | ✅ App + nginx limits |
| Scanned PDF, no text layer | OCR fallback, `low_confidence` flagged | ✅ |
| 500-page tender | Async ingestion, upload still returns <1s | ✅ (no page ceiling — see S7) |
| Duplicate document | Detected by SHA-256, not reprocessed | ✅ |
| Same vendor, second bid | Vendor reused by GSTIN | ✅ |
| Ollama down | Extraction fails; upload/ingestion still succeed | ✅ **[ASSUMPTION — degradation path not directly verified]** |
| Redis down | Ingestion runs inline | ✅ `enqueue.py` probes |
| Portal down | `status=DOWN` → NEEDS_REVIEW, never PASS/FAIL | ✅ |
| Portal returns NOT_FOUND | Distinct from DOWN | ✅ Separate status |
| Compliance before verification | Runs on claimed facts only; gov facts absent | ✅ Findings become NEEDS_REVIEW |
| Compliance before extraction | Requirements synthesized from the rule pack | ✅ `requirement_binding.py` |
| Re-run compliance | Findings replaced, not appended | ✅ + `confirm()` in UI |
| `GET /compliance` before any run | 404, handled silently by the UI | ✅ |
| Missing GSTIN on a bid | GST rule → NEEDS_REVIEW | ✅ **[ASSUMPTION]** |
| MSME rule on a non-MSME bid | Rule skipped entirely via `applies_if` | ✅ |
| FAILed BLOCKER + 26 passes | Band forced HIGH regardless of score | ✅ |
| Rule pack references an unknown fact | NEEDS_REVIEW, not a crash | ✅ **[ASSUMPTION — verify]** |
| Two officers run compliance on one bid concurrently | Last write wins; findings replaced | ⚠️ **No locking — race condition** |
| localStorage disabled | Session doesn't persist; app still works | ✅ try/catch around both read and write |
| Deep link to `/evidence/:ruleId` with no session | Error message + link back | ✅ |
| Report requested before compliance | Clear error | ⚠️ **Unverified** |

---

## 16. TESTING STRATEGY

### Current state **[CONFIRMED]**
**86 backend tests**, all passing, across 5 files: `test_rules_engine.py`, `test_extraction.py`,
`test_extraction_glue.py`, `test_fact_normalization.py`, `test_snippet_guard.py`.
**Frontend tests: 0** (no runner configured — `npm run lint` only).

Coverage is concentrated exactly where it matters most (the deterministic engine, normalization, and
the hallucination guard). The gaps are integration-shaped.

### Recommended additions

**Unit — missing:** `risk/scorer.py` (esp. the BLOCKER-forces-HIGH override), `rules/condition.py`
(`applies_if` grammar, including malformed input), `rules/loader.py` (line-number errors),
`verification/cache.py` (TTL boundary + the naive/aware datetime normalization).

**Integration — missing entirely:** upload → ingest → extract → verify → comply, against a temp
SQLite DB with mock portals. This is the single highest-value test to add.

**API — missing:** FastAPI `TestClient` per endpoint: happy path, 404, malformed input, and the
error-envelope shape.

**Frontend — missing:** Vitest + React Testing Library. Priorities: `SessionContext` persistence,
nav lock states, evidence deep-link refetch, toast lifecycle, compliance re-run confirmation.

**Security:** authz tests become mandatory the moment §13.1 lands.
**Performance:** ingestion time vs page count; concurrent compliance runs.

### Sample test cases

| ID | Feature | Input | Expected | Status |
|---|---|---|---|---|
| T01 | Snippet guard | Snippet absent from page text | Extraction rejected | ✅ Covered |
| T02 | Normalizer | `"Rs. 5,00,00,000"` | `{value:50000000, unit:"INR"}` | ✅ Covered |
| T03 | Engine determinism | Same inputs ×2 | Byte-identical findings | ✅ Covered |
| T04 | `source_priority` | claimed 6.2Cr, gov 4.1Cr, `[government, document]` | FAIL on 4.1Cr, both shown | ✅ Covered |
| T05 | BLOCKER override | 1 FAILed BLOCKER + 26 PASS | band = HIGH | ⚠️ **Add** |
| T06 | Portal DOWN | Adapter raises | `status=DOWN`, finding NEEDS_REVIEW | ⚠️ **Add** |
| T07 | Duplicate upload | Same PDF twice | `duplicate:true`, no reprocess | ⚠️ **Add** |
| T08 | Full pipeline | Sample tender + bid | Findings with evidence pages | ⚠️ **Add (highest value)** |
| T09 | Evidence deep link | `/evidence/REQ-TURNOVER`, fresh reload | Finding refetched and rendered | ⚠️ **Add** |
| T10 | Nav locking | No `tenderId` | Steps 2-5 rendered locked | ⚠️ **Add** |
| T11 | IDOR | Bid UUID of another officer | 403 | ❌ Blocked on §13.1 |

---

## 17. PROJECT FOLDER STRUCTURE

Actual, current **[CONFIRMED]**:

```
project/
├── README.md  CLAUDE.md  docker-compose.yml  .gitignore
├── problem.md      # frontend UI/UX audit (12 issues — all fixed)
├── project.md      # deployment audit (9 issues — 8 fixed)
├── project01.md    # this blueprint
├── backend/
│   ├── app/{api,core,db,models,schemas,services,workers}/
│   ├── rules/default_{goods,works,services}.yaml
│   ├── tests/                    # 86 tests
│   ├── Dockerfile  .dockerignore  requirements.txt  .env.example  alembic.ini
├── frontend/
│   ├── src/{api,components,pages,store,assets}/
│   ├── Dockerfile  .dockerignore  vite.config.js  package.json  index.html
├── data/
│   ├── samples/{tenders,bids}/   # generated demo PDFs
│   ├── mock_portals/*.json       # offline government fixtures
│   ├── uploads/  vectorstore/    # gitignored runtime data
│   └── tenderguard.db            # local SQLite
├── docs/{api,architecture,rule_pack_spec,demo_script}.md
├── infra/nginx/nginx.conf
└── scripts/{generate_sample_pdfs,load_sample_data,run_pipeline_cli,seed_mock_portals}.py
```

This structure is sound. Note there is **no separate top-level `ai/` folder** — AI code lives under
`backend/app/services/{llm,extraction,retrieval}/`, which is correct: it's part of the backend
service, not a separate deployable.

---

## 18. DEVELOPMENT PHASES

Phases 1-7 are **already complete**. The remaining work is 8-10.

| Phase | Scope | Status |
|---|---|---|
| 1 — Setup | Repo, compose, config, structlog | ✅ Done |
| 2 — Database | 11 models, mixins, Alembic, dialect-generic types | ✅ Done |
| 3 — Backend core | 7 routers, error envelope, deps | ✅ Done |
| 4 — Authentication | — | ❌ **Not started (deliberately deferred)** |
| 5 — Frontend | 5 pages, session, stepper nav, toasts | ✅ Done (post-`problem.md`) |
| 6 — Core features | Ingestion, verification, rules, risk, reports, audit | ✅ Done |
| 7 — AI integration | Ollama, guards, normalizers, FAISS retrieval | ✅ Done |
| 8 — Testing | Integration + API + frontend tests | 🔶 Partial (86 unit tests; no integration/frontend) |
| 9 — Security | §13.1 items S1-S5 | ❌ Not started |
| 10 — Deployment | Compose fixed; needs a real run + CI | 🔶 Fixed but **unverified** |

### Phase 8 — Testing *(next, ~2-3 days)*
- **Tasks:** integration test for the full pipeline on temp SQLite + mock portals; API tests per
  endpoint; add T05-T07; set up Vitest + RTL; add 5 frontend tests.
- **Files:** `backend/tests/test_pipeline_integration.py`, `backend/tests/test_api_*.py`,
  `frontend/vitest.config.js`, `frontend/src/**/*.test.jsx`, `frontend/package.json`.
- **Complexity:** Medium. **Done when:** `pytest -q` and `npm test` both pass in CI.

### Phase 9 — Security *(~3-5 days, only if this goes beyond a demo)*
- **Tasks:** S1 auth → S2 ownership → S3 actor-from-session → S5 gate the report → S8 rate limiting.
- **Files:** `models/user.py`, `core/auth.py`, `routes/auth.py`, a migration, `get_current_user`
  wired into every route, frontend login page + protected routes.
- **Complexity:** High — touches every endpoint and the whole frontend routing layer.
- **Done when:** an unauthenticated request to any non-health endpoint returns 401, and an
  authenticated request for another officer's bid returns 403.

### Phase 10 — Deployment *(~1-2 days)*
- **Tasks:** install Docker → actually run `docker compose up` → smoke-test through :80 (this is the
  **critical unvalidated step**) → add GitHub Actions running pytest + lint + `docker compose build`
  → decide on a hosted target.
- **Complexity:** Low-medium, but **blocking** — the compose fixes are unverified.

---

## 19. TEAM DISTRIBUTION

**[REQUIRED INFO — Critical]** I don't know your team size, names, or skills. The split below is a
**proposal for a typical 6-person SIH team**, structured so no two people touch the same files.

| Member | Owns (files) | Deliverables | Skills needed |
|---|---|---|---|
| **A — Backend/API** | `app/api/`, `app/core/`, `app/schemas/` | Endpoints, error envelope, API tests | FastAPI, Pydantic |
| **B — Data/Pipeline** | `app/services/{ingestion,retrieval}/`, `app/models/`, migrations | PDF/OCR pipeline, FAISS, schema | PyMuPDF, OCR, SQLAlchemy |
| **C — AI/Extraction** | `app/services/{llm,extraction}/`, `prompts/` | Prompts, guards, normalizers, extraction accuracy | Prompt engineering, Pydantic |
| **D — Rules/Verification** | `app/services/{rules,risk,verification,compliance}/`, `rules/*.yaml` | Engine, adapters, scoring, rule packs | Pure-function design, API integration |
| **E — Frontend** | `frontend/src/**` | All 5 pages, components, frontend tests | React, Tailwind |
| **F — DevOps/QA/Docs** | `docker-compose.yml`, `infra/`, `.github/`, `docs/`, `scripts/` | Compose validation, CI, docs, demo rehearsal | Docker, CI, technical writing |

**Collision risks to manage:** C and D both touch fact *keys* — agree the dotted-path vocabulary
(`financials.avg_annual_turnover`) in writing first. A and E share the API contract — freeze
`docs/api.md` before parallel work. **F owns the docs, so C1-C4 in §14.2 are F's to close.**

---

## 20. GIT / VERSION CONTROL STRATEGY

**[CONFIRMED]** Current state: a git repo with **one commit** (`2262a87 "project"`) and ~20
uncommitted modified/untracked files. There is no branching model in use.

**This is the most immediately fixable process risk.** All the UI/UX and deployment work from this
session is uncommitted — one bad command loses it.

### Recommended workflow
```
main            ← always demo-ready, tagged releases
└── develop     ← integration branch
    ├── feature/auth
    ├── feature/officer-review
    ├── feature/integration-tests
    └── fix/compose-smoke-test
```

**Branch naming:** `feature/<short-name>`, `fix/<short-name>`, `docs/<short-name>`.
**Commits:** Conventional Commits — `feat(rules): add date_before operator`, `fix(nginx): stop
stripping /api prefix`, `test(engine): cover BLOCKER band override`.
**PRs:** one reviewer minimum; must state what was manually tested.
**Merge:** squash into `develop`; merge commit `develop` → `main`. **Tags:** `v0.1.0-mvp`,
`v1.0.0-sih-submission`.

```bash
git checkout -b develop
git add -A && git commit -m "feat: UI/UX and deployment fixes from audit"
git checkout -b feature/integration-tests develop
# ... work ...
git tag -a v0.1.0-mvp -m "MVP: full pipeline, 86 tests"
```

> ⚠️ **Do this before anything else.** Also verify nothing sensitive is staged — `.env` files are
> correctly gitignored (**verified**), but re-check after any `git add -A`.

---

## 21. DEPLOYMENT ARCHITECTURE

### Development (this machine) **[CONFIRMED working]**
SQLite + native Ollama (`qwen2.5:3b`) + native uvicorn + `npm run dev`. Docker unavailable
(Postgres CDN blocked by a network-level 403; Docker not installed).

### Demo / staging — Docker Compose **[FIXED, UNVERIFIED]**
```
docker compose up
  postgres ─┐
  redis ────┼─→ migrate (one-shot) ──┐
  ollama ───┴─→ ollama-pull (one-shot)┴─→ api ─┐
                                       worker  ├─→ nginx :80
                                       frontend ┘
```
`migrate` and `ollama-pull` gate `api`/`worker` via `service_completed_successfully`, so a cold
`docker compose up` needs no manual migration or model pull. **⚠️ Never actually executed.**

### Production **[REQUIRED INFO — no target chosen]**
Blocked on §13.1 (auth) regardless of host. When you get there:

| Layer | Option | Note |
|---|---|---|
| Frontend | Static `dist/` on nginx/CDN | Build with `npm run build`, drop the dev server |
| Backend | Container on a VM | Gunicorn + uvicorn workers, **not** `--reload` |
| Database | Managed Postgres | Only `DATABASE_URL` changes — models are dialect-generic |
| LLM | Ollama on a GPU VM | Data sensitivity argues against a hosted API |
| Files | S3-compatible object store | Replaces local `UPLOAD_DIR` |
| Secrets | Secret manager | **Rotate the compose `tenderguard:tenderguard` password** |
| HTTPS | Let's Encrypt at nginx | Mandatory — bid data in transit |

### Environment variables
`backend/.env` (gitignored, `.env.example` tracked): `DATABASE_URL`, `REDIS_URL`,
`OLLAMA_BASE_URL`/`OLLAMA_MODEL`, `VERIFICATION_MODE`, `UPLOAD_DIR`/`VECTORSTORE_DIR`/
`MOCK_PORTAL_DIR`, `MAX_UPLOAD_MB`, `CORS_ORIGINS`, `TESSERACT_CMD`, live portal keys.
`frontend/.env`: `VITE_API_BASE_URL` (leave unset to use the same-origin proxy), `VITE_PROXY_TARGET`.

---

## 22. DOCUMENTATION CHECKLIST

| Doc | Status |
|---|---|
| README | ✅ Excellent — architecture, pitfalls, anti-scope, demo script |
| Problem statement | ✅ README §1-2 |
| System architecture | ✅ `docs/architecture.md` |
| API documentation | 🔶 `docs/api.md` — **stale: C1, C2** |
| Database documentation | 🔶 Models are well-commented; no consolidated ER doc (§8 fills this) |
| Rule pack spec | ✅ `docs/rule_pack_spec.md` — genuinely good |
| Setup guide | ✅ README §12 (rewritten: Option A compose / Option B native) |
| Demo script | ✅ `docs/demo_script.md` |
| Developer guide | ✅ `CLAUDE.md` — conventions + hard constraints |
| Deployment guide | 🔶 Compose documented but unverified |
| Testing documentation | ❌ Missing |
| Security documentation | ❌ Missing (§13 is the first draft) |
| User guide (for officers) | ❌ Missing |

---

## 23. MVP vs FUTURE

### MVP — ✅ **already complete**
Tender+bid upload, ingestion with OCR fallback, LLM extraction with guards, mock verification,
deterministic rule engine, risk scoring, compliance matrix, evidence viewer, PDF report, audit
trail, offline operation.

### Version 2 — the highest-value next features
1. **Officer review step** (F14/C4) — makes good on a claim the README already makes.
2. **Integration + frontend tests** (Phase 8).
3. **Authentication + authorization** (§13.1) — the gate to any real deployment.
4. **Multi-bid comparison** — rank all bids for one tender. *This is the biggest demo-impact feature
   not yet built:* the real officer workflow is "which of these 8 vendors qualifies?", not one bid.
5. **Expose semantic search in the UI** (C2) — already built, currently invisible.
6. **Rule pack editor UI** — turns "officer-editable" from true-in-principle to true-in-practice.
7. **Finding override with justification**, written to the audit trail.

### Future
Live GST/Udyam at scale; bulk upload; analytics across tenders; vendor risk history; e-procurement
portal integration; regional language tenders; extraction-confidence scoring + eval harness.

### Explicitly out of scope **[CONFIRMED — README §10]**
Blockchain, multi-agent orchestration, chatbot, custom model training, Kubernetes, heavy RAG
infrastructure, 10 portal integrations. **This restraint is a strength — don't relitigate it.**

---

## 24. FEASIBILITY ANALYSIS

| Dimension | Rating | Notes |
|---|---|---|
| Technical feasibility | ✅ **Proven** — it already works end-to-end |
| Development complexity | Moderate-High | 11 tables, 9 service modules, LLM + OCR + rules |
| Cost | Very low | All open-source; local LLM = no API bills |
| Time (remaining) | ~1-2 weeks for Phases 8-10 |
| Skills required | Python/FastAPI, React, prompt engineering, Docker, PDF/OCR |
| AI complexity | Moderate — **deliberately kept low** by keeping the LLM out of decisions |
| Infrastructure | Low for demo; GPU VM for production LLM |
| Scalability | Untested — architecture supports it (Celery, stateless API) |
| Security risk | ⚠️ **High if deployed as-is** — no auth; low as a local demo |

**Overall: MODERATE** — and notably *de-risked* by good architectural decisions. The hard parts
(determinism, provenance, offline operation, hallucination control) are solved. What remains is
conventional work: tests, auth, and one verified deployment run.

**Biggest risks, ranked:**
1. **Uncommitted work** — a single commit in the repo, ~20 files unstaged. Fix today (§20).
2. **Compose never executed** — all Phase-10 fixes are unverified (C5).
3. **No auth** — caps this at "demo" until fixed.
4. **Model mismatch** (C3) — the demo may behave differently than documented.

---

## 25. FINAL PROBLEM → SOLUTION MAPPING

| Problem | Feature | Technology | Implementation | Result |
|---|---|---|---|---|
| Manual verification takes days | Automated portal verification | Adapter pattern + TTL cache | `services/verification/` | Seconds, not days |
| Vendors overstate facts | Government-first fact resolution | YAML `source_priority` | `rules/engine.py` | Claim vs record surfaced as FAIL |
| Verdicts unauditable | Evidence on every finding | 1:1 FK + UNIQUE constraint | `models/finding.py` | Page + snippet + hash per verdict |
| No decision history | Append-only audit trail | Insert-only table | `audit/trail.py`, `GET /audit` | Full action history |
| Scanned PDFs | OCR fallback | PyMuPDF → OpenCV + Tesseract | `ingestion/ocr.py` | Scanned docs usable, uncertainty flagged |
| Messy units | Single normalization boundary | Custom normalizers | `extraction/normalizers.py` | Typed values downstream |
| LLM hallucination | 4-layer guardrail | temp 0 + JSON schema + snippet guard + no-LLM-decisions | `llm/`, `extraction/` | Non-verbatim output rejected |
| Non-reproducible verdicts | Pure-function engine | No LLM, no I/O | `rules/engine.py` | Same input → same output, always |
| Portal downtime | Graceful degradation | Adapters return `DOWN` | `verification/adapters/` | Never a false PASS/FAIL |
| Ambiguous legal text | Fixed taxonomy + review bucket | Enum-style category | `models/requirement.py` | No silent force-fitting |
| Rules need officer edits | YAML rule packs | Fixed-grammar parser, never `eval()` | `rules/{loader,condition}.py` | Editable without code changes |
| Slow uploads | Async ingestion w/ fallback | Celery + Redis probe | `ingestion/enqueue.py` | <1s response, works without Redis |
| Officer loses their place | Stepper nav + context bar | React Context | `NavBar.jsx` | Pipeline state always visible |
| Silent action failures | Toast notifications | Context provider | `ToastContext.jsx` | Every action confirms or errors |
| Evidence lost on refresh | Deep-linkable evidence | Route param + refetch | `EvidenceViewer.jsx` | Shareable, reload-safe URLs |
| Report needed for the file | PDF generation | ReportLab | `reports/pdf_builder.py` | Summary + matrix + evidence + hashes |
| Demo needs no internet | Mock mode + local LLM | JSON fixtures + Ollama | `data/mock_portals/` | Runs with WiFi off |
| **No access control** | — | — | ❌ **UNSOLVED** | **See §13.1 — the one major gap** |

Every problem except authentication has a corresponding implemented solution.

---

## 26. REQUIRED INFORMATION

### 🔴 Critical — blocks correct planning

1. **Team size, names, and skills.** §19 is a generic proposal. I cannot assign real work without
   knowing who's on the team.
2. **Deadline / submission date.** Determines whether Phase 9 (auth, ~3-5 days) is realistic.
3. **Is this evaluated as a demo, or must it be deployable?** Auth is optional for the former and
   mandatory for the latter. This single answer changes the whole roadmap.
4. **Can Docker be installed on the demo machine?** All Phase-10 fixes are unverified (C5). If not,
   the native path becomes canonical and the compose services should be pruned.
5. **Which model is canonical — `llama3.1:8b` or `qwen2.5:3b`?** (C3) Affects extraction quality and
   what you should rehearse against.

### 🟡 Important — affects design decisions

6. **Do you have real GST/Udyam API access?** Credentials, provider, rate limits. Live adapters exist
   but are unconfigured. README targets "2 real integrations" — is that achievable?
7. **Is the officer review step (C4) required?** README claims it; it isn't built.
8. **Is multi-bid comparison expected?** The real workflow is "which of 8 vendors qualifies?" — this
   is the largest gap between the current single-bid UI and actual officer work.
9. **Expected scale.** Bids per tender, tenders per month, concurrent officers. Determines whether
   the concurrency race in §15 matters.
10. **Any SIH-mandated deliverables?** Presentation, video, specific documentation format.

### 🟢 Optional

11. Do you want the semantic search feature (C2) exposed in the UI?
12. Should audit logs be exportable for a formal audit?
13. Is a regional-language requirement anticipated?
14. Any institutional branding required on the PDF report?

---

## 27. FINAL BLUEPRINT (condensed)

| # | Element | Summary |
|---|---|---|
| 1 | **Problem** | Manual verification of vendor bids against tender criteria is slow, error-prone, and unauditable |
| 2 | **Solution** | Extract with AI, verify against government records, decide with a deterministic rule engine, evidence every verdict |
| 3 | **Users** | Procurement officers (1 implicit role today; 4 proposed) |
| 4 | **Features** | Upload → ingest+OCR → extract → verify → rules → risk → matrix → evidence → PDF → audit |
| 5 | **Architecture** | nginx → FastAPI → 9 service modules → Postgres/SQLite + Redis/Celery + Ollama + FAISS |
| 6 | **Stack** | React 19/Vite/Tailwind · FastAPI/SQLAlchemy 2.0/Alembic · Postgres 16 · Ollama · FAISS · PyMuPDF+Tesseract · ReportLab |
| 7 | **Database** | 11 tables; `Finding`↔`Evidence` 1:1 enforced; append-only `AuditLog`; dialect-generic types |
| 8 | **APIs** | 7 routers under `/api/v1`; uniform `{code,message,detail}` envelope |
| 9 | **AI** | Extraction only, behind 4 guardrails; **hard boundary — no LLM below the extraction line** |
| 10 | **Security** | ⚠️ No auth/authz — the one critical gap (S1-S5) |
| 11 | **Testing** | 86 backend unit tests ✅; integration + frontend tests ❌ |
| 12 | **Structure** | `backend/app/{api,core,db,models,schemas,services,workers}` + `frontend/src/{api,components,pages,store}` |
| 13 | **Roadmap** | Phases 1-7 ✅ · 8 Testing 🔶 · 9 Security ❌ · 10 Deployment 🔶 |
| 14 | **Team** | 6-role split proposed — **needs your team's real composition** |
| 15 | **Deployment** | Native ✅ · Compose fixed but unverified ⚠️ · Production undefined |
| 16 | **Future** | Officer review · multi-bid comparison · auth · rule editor · live portals |

---

## ⭐ WHAT SHOULD WE BUILD FIRST?

In strict order. Items 1-3 are same-day and de-risk everything else.

### 1. Commit the work — **today, before anything else** ⏱️ 15 min
One commit exists; ~20 files of finished UI/UX and deployment work are uncommitted. Create
`develop`, commit, tag `v0.1.0-mvp`. Nothing else matters if this is lost.

### 2. Actually run `docker compose up` ⏱️ 2-4 h
Every Phase-10 fix is unverified (C5). Install Docker, run it cold, and smoke-test **through
port 80** — not `:8000` — to confirm the nginx prefix fix. Until this passes, treat "one-command
deploy" as a claim, not a fact.

### 3. Fix the four doc contradictions ⏱️ 1 h
C1 (`/audit` exists), C2 (document `/tenders/{id}/search`), C3 (pick a canonical model), C4 (build
the review step or drop the claim). Cheap, and judges read docs.

### 4. Write the full-pipeline integration test ⏱️ 1 day
`upload → ingest → extract → verify → comply` on temp SQLite with mock portals. Highest-value single
test: it guards the exact path the demo depends on.

### 5. Decide: auth or not? ⏱️ decision now, 3-5 days if yes
Answer §26 Q3. Demo-only → skip Phase 9 and invest in multi-bid comparison instead (far more
demo impact). Deployable → Phase 9 is mandatory and starts now.

### 6. Rehearse the demo offline ⏱️ 2 h
README says rehearse twice, once with the internet disconnected. With `qwen2.5:3b` rather than the
documented model, **verify the turnover-mismatch moment actually lands** — that single screen is the
project's whole argument.

> **What NOT to do next:** don't add features. The MVP is complete and the architecture is sound.
> The gap between this project and a winning one is *verification and polish* — a deployment you've
> actually run, tests that prove the pipeline, and a rehearsed demo — not more code.
