# TenderGuard — Problem Definition

**Problem ID:** SIH26100 (Smart India Hackathon) — AI Tender & Vendor Compliance Verification
**Domain:** GovTech · Document AI · Procurement compliance
**Companion documents:** `readme0111.md` (architecture) · `project01.md` (master blueprint) · `docs/`

---

## 1. The problem in one sentence

> Government procurement officers verify vendor eligibility claims **by hand**, against **documents
> that vendors write about themselves** — a process that takes days per tender, catches almost no
> deliberate overstatement, and leaves behind no record that can defend the decision when it is
> challenged.

---

## 2. The problem in plain language

A government officer receives a **tender document** — the rules of the contract:

> *"Bidders must have a minimum average annual turnover of ₹5 crore, a valid and active GST
> registration, at least 3 years of relevant experience, and must not appear on any debarment list."*

Then a pile of **vendor bids** arrives — companies describing themselves:

> *"Our average annual turnover is ₹6.2 crore. Our GSTIN is 27AABCU9603R1ZM. We have 7 years of
> experience in road construction equipment supply."*

Today the officer must, for every claim in every bid:

1. Read the tender PDF and write down each eligibility rule.
2. Read the bid PDF and find the matching claim.
3. Open the GST portal, type the GSTIN, and check whether the registration is real and active.
4. Open the Udyam/MSME registry and check the certificate if MSME benefits are claimed.
5. Check the debarment/blacklist databases.
6. Compare each claim to each rule, decide PASS or FAIL, and record why.

For one tender with eight bidders and twenty-seven eligibility criteria, that is **216 manual
comparisons and dozens of portal lookups**. It takes days. Under deadline pressure, steps get
skipped — and the step most often skipped is the expensive one: actually checking the claim against
the government record.

**The consequence:** a company that does not qualify wins a public contract, and nobody can later
reconstruct how the decision was made.

---

## 3. Who is affected

| Stakeholder | How the problem hurts them |
|---|---|
| **Procurement / tender evaluation officer** (primary user) | Days of repetitive work per tender; personally accountable for a decision they cannot fully verify in the time available |
| **The buying department** | Awards contracts on unverified eligibility; capability failures surface only after the contract is running |
| **Honest competing vendors** | Lose to bidders who overstated turnover, experience, or MSME status and were never checked |
| **Audit / vigilance staff** | Cannot reconstruct why a bid passed — the working notes are not a record |
| **The public exchequer** | Pays for work awarded to under-qualified suppliers |

---

## 4. Root causes — why this is hard, not just tedious

| # | Root cause | Why it resists a simple fix |
|---|---|---|
| RC1 | **The bid is self-reported** | Nothing in the document is evidence of itself. Truth lives in a *different system* (GST, Udyam, debarment lists) that must be reached separately for every claim. |
| RC2 | **Both inputs are unstructured PDFs** | Tender rules and vendor claims are prose and tables, written differently by every department and every vendor. There is no schema to parse. |
| RC3 | **Many bid documents are scans** | No text layer at all — the content is a picture of text. |
| RC4 | **Numbers are written a dozen ways** | `₹5,00,00,000`, `Rs. 5 crore`, `5 Cr`, `50 million`, `500 lakh` — all the same figure. Naive string comparison silently produces wrong verdicts. |
| RC5 | **Eligibility language is legal and conditional** | *"...or, in the case of a Micro or Small Enterprise registered under Udyam, a relaxation of 25% shall apply."* Rules apply only sometimes, depending on other facts. |
| RC6 | **A verdict must be defensible, not merely correct** | A rejected bidder can legally challenge the decision. "The system said so" is not an answer. Every verdict needs its source page and the government record behind it. |
| RC7 | **Government portals are unreliable** | Down, rate-limited, captcha'd, or slow. A verification system that treats an outage as a failed check produces false rejections. |
| RC8 | **The obvious AI approach makes it worse** | An LLM that reads *and decides* is non-deterministic, cannot cite, and hallucinates — the three properties least acceptable in a procurement audit. |

---

## 5. The eight concrete problems, and how TenderGuard answers each

### P1 — Manual claim verification is slow

- **Who:** procurement officers · **Frequency:** every bid, every tender, continuously
- **Cause:** every claim requires a separate manual portal lookup
- **If unsolved:** days of officer time per tender; verification quietly gets skipped under deadline pressure
- **Solution:** `POST /bids/{id}/verification` — an adapter registry queries GST / Udyam / debarment
  and caches results per bid+portal with a TTL (`services/verification/`)

### P2 — Vendors overstate facts, and nobody cross-checks

- **Who:** the buying department, and every honest competing vendor
- **Cause:** the bid document is self-reported; checking it is expensive (RC1)
- **If unsolved:** contracts awarded on false eligibility
- **Solution:** `source_priority: [government, document]` in the rule pack. The engine resolves each
  fact from the **government record first**, so a claimed ₹6.2 Cr against a GST-recorded ₹4.1 Cr
  surfaces as a FAIL with both numbers shown side by side. *This is the single mechanism that turns
  a document reader into a fraud detector.*

### P3 — "Where did this number come from?" is unanswerable

- **Cause:** verification lives in an officer's notes, not in a record (RC6)
- **If unsolved:** decisions cannot survive an audit or a vendor challenge
- **Solution:** an `Evidence` row (document, page number, bounding box, verbatim snippet, document
  SHA-256) is **1:1 with every `Finding`**. `compliance/service.py` resolves a real page reference
  with ordered fallbacks, so a finding can never be persisted without one. Plus an append-only
  `AuditLog` for every upload, verification, compliance run and report download.

### P4 — Scanned and poor-quality PDFs

- **Cause:** no embedded text layer (RC3)
- **If unsolved:** the officer retypes figures by hand, or the document is excluded from checking
- **Solution:** any page with under ~50 characters of embedded text falls back to OCR (OpenCV
  deskew/denoise + Tesseract), which sets `low_confidence` rather than silently trusting bad output.
  Uncertainty is surfaced to the officer instead of being hidden.

### P5 — Chaotic units and number formats

- **Cause:** human-written figures with no convention (RC4)
- **If unsolved:** comparison bugs produce confidently wrong verdicts
- **Solution:** exactly **one** normalization boundary (`extraction/normalizers.py`,
  `fact_normalization.py`) where messy strings become typed values. Nothing downstream ever parses a
  raw string.

### P6 — LLM hallucination would be fatal here

- **Cause:** generative models invent plausible text (RC8)
- **If unsolved:** an invented eligibility requirement or an invented vendor claim enters a legal record
- **Solution:** a four-layer guardrail —
  1. temperature 0 with a pinned seed,
  2. forced JSON validated against a Pydantic schema with a repair loop (`llm/json_guard.py`),
  3. **`snippet_guard.py`** — any extraction whose quoted snippet is not *literally present* in that
     page's text is rejected outright,
  4. the LLM is structurally excluded from the decision path (see §6).

### P7 — Government portals are down, rate-limited, or captcha'd

- **Cause:** external dependency outside our control (RC7)
- **If unsolved:** an outage becomes a false PASS or a false FAIL
- **Solution:** adapters degrade to `status = DOWN` and never raise; the affected finding becomes
  `NEEDS_REVIEW`, escalating to a human rather than guessing. Mock mode (`data/mock_portals/*.json`)
  exists from day one, so the entire system runs with the network off.

### P8 — Requirements are written in ambiguous legal language

- **Cause:** legal drafting conventions (RC5)
- **If unsolved:** the system force-fits an unclear clause into the wrong category and gets it wrong silently
- **Solution:** a fixed taxonomy (`turnover | experience | certification | registration | financial |
  technical | msme | debarment | manual_review`). Anything that does not map cleanly goes to
  `manual_review` — an explicit "a human must read this" bucket, never a guess. Conditional clauses
  are expressed as `applies_if` in the rule pack (e.g. `bid.claims_msme_benefit == true`).

---

## 6. Why existing approaches fall short

| Approach | What it does | Why it does not solve this problem |
|---|---|---|
| **Fully manual** — read + look up | The status quo | Days per tender; inconsistent between officers; no audit trail beyond personal notes |
| **e-Procurement portals** (GeM, CPPP) | Handle bid *submission and workflow* | They manage the process, not the **semantic verification** of a claim against a government record. The comparison is still manual. |
| **Generic "upload PDF → ask an LLM"** | Answers questions about the document | The LLM both *reads* and *decides*: non-deterministic (a different answer on re-run), unciteable, and prone to hallucination. **It cannot be defended in a procurement audit.** |
| **A RAG chatbot over the tender** | Retrieves relevant clauses | Retrieval alone produces no verdict, no weighting, no cross-check against government data, and no reproducibility. |

### The design consequence — our USP

> **The golden rule: the LLM extracts. It never decides.**

Every `PASS` / `FAIL` / `NEEDS_REVIEW` comes from `backend/app/services/rules/engine.py` — a **pure
function** with no LLM calls and no I/O, so the same input always produces the same output. The
LLM's only job is turning unstructured PDF text into structured, snippet-backed fields, and even
that is guarded four ways.

Five properties that distinguish this from a document chatbot:

1. **Deterministic rule engine** — verdicts come from officer-editable YAML, not from model output.
2. **Government cross-verification** — `source_priority` puts the government record ahead of the
   vendor's document. This is *how an inflated claim gets caught*.
3. **Hallucination guardrail** — non-verbatim snippets are rejected before reaching the database.
4. **Evidence on every finding** — a 1:1 `Finding`↔`Evidence` relationship; no verdict without a page.
5. **Runs fully offline** — mock verification mode plus a local Ollama model; the demo works with
   WiFi switched off.

---

## 7. Master problem → solution table

| Problem | Cause | Current practice | Its limitation | TenderGuard's answer | Expected result |
|---|---|---|---|---|---|
| Slow manual verification | Per-claim portal lookups | Officer + browser | Days per tender | Adapter registry + TTL cache | Verification in seconds |
| Vendor overstates turnover | Self-reported bid | Occasional spot checks | Rarely caught | `source_priority: government` first | Mismatch surfaces as FAIL, both figures shown |
| Unauditable verdicts | Notes, not records | Paper file | Cannot defend a challenge | `Evidence` 1:1 with `Finding` + append-only `AuditLog` | Every verdict traceable to a page |
| Scanned PDFs unreadable | No text layer | Manual retyping | Slow, error-prone | PyMuPDF → OCR fallback + `low_confidence` | Scanned docs usable, uncertainty visible |
| LLM hallucination | Generative model | — (fatal in naive designs) | Invented facts | temp 0 + JSON guard + snippet guard + no-LLM-decisions | Non-verbatim output rejected |
| Portal downtime | External dependency | Retry manually | False verdicts | Degrade to `DOWN` → `NEEDS_REVIEW` | Never a false PASS/FAIL |
| Messy units | Human-written figures | Manual reading | Comparison bugs | Single normalization boundary | Typed values reach the engine |
| Ambiguous legal text | Legal drafting | Officer judgment | Inconsistent between officers | Fixed taxonomy + `manual_review` bucket | No silent force-fitting |
| Non-reproducible decisions | LLM in the decision path | — | A different answer each run | Pure-function rule engine | Same input → same output, always |
| Rules need officer edits | Criteria vary per tender | Hard-coded logic | Developer needed for every change | YAML rule packs, fixed-grammar `applies_if`, never `eval()` | Editable without code changes |

---

## 8. Scope

### In scope

Tender + bid PDF upload · ingestion with OCR fallback · LLM extraction of requirements and claimed
facts with guardrails · GST / Udyam / debarment verification (mock and live) · deterministic YAML
rule engine · weighted risk scoring · compliance matrix with evidence · semantic clause search ·
PDF compliance report · append-only audit trail · fully offline operation.

### Explicitly out of scope

Blockchain · multi-agent orchestration · a chatbot interface · custom model training · Kubernetes ·
heavy RAG infrastructure · integrations with ten different portals.

*This restraint is deliberate. The problem is solved by determinism and provenance, not by more AI.*

---

## 9. How we know the problem is solved

| Success criterion | Measured by | Status |
|---|---|---|
| An officer gets a full compliance matrix without manual portal lookups | End-to-end run: upload → extract → verify → compliance | ✅ Works end-to-end |
| Every verdict cites a page and a snippet | DB invariant: no `Finding` without `Evidence` | ✅ Enforced in code |
| The same documents always produce the same verdict | Pure-function engine, temp 0, pinned seed | ✅ Covered by tests |
| An inflated claim is caught against the government record | `source_priority` resolution + demo fixture | ✅ Demonstrated |
| A portal outage never produces a false PASS/FAIL | Adapters return `DOWN` → `NEEDS_REVIEW` | ✅ |
| The whole demo runs with no internet | Mock mode + local Ollama | ✅ |
| A hallucinated extraction cannot reach the database | `snippet_guard` rejection tests | ✅ |
| Stated goal: ~80% less verification effort | *No benchmark exists in the repo* | ⚠️ Claimed, not measured |

---

## 10. What the project does **not** yet solve

Stated plainly, because an honest gap list is part of the problem definition.

### Blocking for any real deployment

| # | Gap | Consequence |
|---|---|---|
| S1 | **No authentication.** Anyone who can reach the API is `"officer"` | The system is a local demo, not a deployable service |
| S2 | **No authorization.** Any caller can read any bid by its UUID | Insecure direct object reference on commercially sensitive documents |
| S3 | **The audit trail is forgeable.** The actor comes from the client-controlled `X-Actor` header | *The entire auditability claim depends on fixing this* — it is a one-line change once S1 lands |
| S4 | **Documents are unprotected at rest.** PDFs sit on disk with no encryption or ACL | Bid documents are commercially sensitive and legally privileged |
| S5 | **The report endpoint is unauthenticated** — it streams a full compliance PDF to anyone with the UUID | Hard-to-guess UUIDs are not access control |

### Known functional gaps

- **No officer review step in the UI.** The `human_reviewed` flag exists on `Requirement` and the
  `PATCH` endpoint works, but no screen sets it — while the README lists officer review as a
  hallucination countermeasure. Either build it or drop the claim.
- **No multi-bid comparison.** The real officer question is *"which of these eight vendors
  qualifies?"*, and the system currently answers one bid at a time. This is the highest-impact
  feature not yet built.
- **Semantic clause search is invisible.** `GET /tenders/{id}/search` is implemented and working, but
  is absent from `docs/api.md` and unreachable from the UI.
- **No rule pack editor.** Rules are officer-editable in principle (YAML, no code changes) but in
  practice require file access.
- **No finding override.** A reviewer cannot overturn a `NEEDS_REVIEW` with a logged justification.

### Unverified behaviour (edge cases to confirm)

Empty or 0-byte PDF · a non-PDF renamed to `.pdf` (magic-byte check unverified) · password-protected
PDF · report requested before compliance has run · two officers running compliance on one bid
concurrently (last write wins — no locking) · rate limiting (absent everywhere) · no page-count
ceiling or per-document processing timeout on untrusted PDFs.

### Documentation contradictions to resolve

- `docs/api.md` says there is no `/audit` list endpoint — but `routes/audit.py` implements it. Stale doc.
- The README and `.env.example` specify `llama3.1:8b`; the working `.env` on this machine uses
  `qwen2.5:3b` (deliberate — the 3B model fits this hardware), so extraction quality differs from
  what is documented. Decide which is canonical before judging the demo.
- `CLAUDE.md` calls Docker Compose the intended one-command path, but Docker is not installed on this
  machine — the compose fixes are correct by inspection and **have never actually been executed**.

**Bottom line:** every problem in §5 has a corresponding implemented solution. The one major
unsolved problem is **access control** — and until it is solved, TenderGuard is a working prototype
rather than a deployable system.
