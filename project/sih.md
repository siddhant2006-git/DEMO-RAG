# TenderGuard — SIH Idea Submission Deck (slide-by-slide copy)

**Problem Statement ID:** SIH26100 · **Title:** AI Tender & Vendor Compliance Verification
**Theme:** Smart Automation / GovTech · **Category:** Software
**Team name:** `<fill in>` · **Team ID:** `<fill in>` · **Institute:** `<fill in>`

This file is the **content** for the official SIH idea-submission PPT (6 slides). Each section below
is one slide: the bullets are already sized for a slide, and the *Speaker notes* under each are what
you say out loud — do not put those on the slide. Sourced from `problem.md` and `solution.md`.

**How to use it:** copy each "SLIDE n" block into the SIH template as-is, then build the one visual
named in *Put on the slide*. Keep to 6 slides — the template is fixed and judges score against it.

---

## SLIDE 1 — Title / Idea details

> The official template auto-fills most of this. Confirm every field matches your registration.

| Field | Value |
|---|---|
| Problem Statement ID | SIH26100 |
| Problem Statement Title | AI Tender & Vendor Compliance Verification |
| Theme | Smart Automation / GovTech |
| PS Category | Software |
| Team Name / Team ID | `<fill in>` |
| Idea title (one line) | **TenderGuard — the LLM reads, a deterministic engine decides** |

**One-line pitch (say this, don't write it):**
> "TenderGuard turns days of manual eligibility checking into seconds — and unlike a chatbot, every
> single PASS or FAIL it produces cites a page, a snippet and a government record, so it can be
> defended in an audit."

---

## SLIDE 2 — Proposed Solution

### The problem, in one look

- A tender says: *"minimum ₹5 crore turnover, active GST, 3 years' experience, not debarred."*
- Eight bidders × twenty-seven criteria = **216 manual comparisons** + dozens of portal lookups.
- The bid is **self-reported** — the truth lives in GST / Udyam / debarment systems, checked by hand.
- Under deadline pressure the expensive step gets skipped: **actually verifying the claim.**
- Result: an unqualified vendor wins a public contract, and nobody can reconstruct the decision.

### Our solution

- Officer uploads the **tender PDF** and the **bid PDFs**. Nothing else to do.
- An LLM **reads** both into structured, page-cited facts — it never gives an opinion.
- Each fact is **cross-checked against the government record** (GST · Udyam · debarment).
- A **deterministic YAML rule engine** issues every PASS / FAIL / NEEDS-REVIEW.
- Output: a **compliance matrix**, a weighted **risk score**, a **PDF report**, an **audit trail**.

### How it addresses the problem

| The officer's pain | What TenderGuard does |
|---|---|
| Days of portal lookups | One request checks every portal, results cached |
| Vendor overstates turnover | Government value is resolved **first** — the mismatch surfaces as a FAIL, both figures shown |
| "Where did this number come from?" | Every verdict carries page + verbatim snippet + document SHA-256 |
| Scanned bids unreadable | OCR fallback that **flags** low confidence instead of faking it |
| Portal is down | Verdict degrades to NEEDS-REVIEW — never a false PASS or FAIL |

### Innovation and uniqueness

> **The golden rule: the LLM extracts. It never decides.**

- Every verdict comes from a **pure function** — same input, same output, forever. A chatbot cannot
  promise this, and a procurement audit requires it.
- **Government-first fact resolution** (`source_priority`) is what turns a document reader into a
  fraud detector.
- **Four-layer hallucination guardrail** — temperature 0 + pinned seed · schema-validated JSON with a
  repair loop · a snippet not literally on the page is **rejected** · and the model is structurally
  absent from the decision path.
- **Runs fully offline** — mock portal mode + a local Ollama model. The demo works with WiFi off.

**Put on the slide:** left half = the "216 manual comparisons" pain, right half = a screenshot of the
compliance matrix with one red FAIL row expanded to show claimed ₹6.2 Cr vs GST-verified ₹4.1 Cr.

*Speaker notes:* Lead with the fraud catch, not the architecture. The single most persuasive sentence
in this deck is: "the bid says 6.2 crore, the GST record says 4.1 — we show both, and we fail it."

---

## SLIDE 3 — Technical Approach

### Technologies used

| Layer | Stack |
|---|---|
| Backend | Python 3.11 · FastAPI · SQLAlchemy + Alembic |
| Async | Celery + Redis (optional — falls back to inline execution) |
| Document AI | PyMuPDF (text + word boxes) · OpenCV (deskew/denoise) · Tesseract OCR |
| LLM | **Ollama, local** — temperature 0, pinned seed. No data leaves the machine |
| Retrieval | Sentence-Transformers MiniLM (384-dim) · FAISS, with a NumPy fallback |
| Rules | Officer-editable **YAML rule packs** — no code change to edit a criterion |
| Reports | ReportLab PDF · append-only audit log |
| Frontend | React 19 · Vite · Tailwind |
| Storage | PostgreSQL (SQLite for the offline demo) |

### Methodology — the pipeline

```
 Tender PDF ─┐
             ├─►  INGEST      PyMuPDF text + boxes; page < 50 chars ─► OCR fallback
 Bid PDF ────┘                                    (low confidence is flagged, never hidden)
                     │
                     ▼
                  EXTRACT     Local LLM, temp 0, forced JSON
                     │        ✗ snippet not verbatim on the page → REJECTED
                     ▼
                 NORMALIZE    "₹5,00,00,000" · "5 Cr" · "500 lakh" → 50000000.0
                     │        (exactly one place in the codebase parses a string)
                     ▼
                   VERIFY     GST · Udyam · Debarment adapters → UP / NOT_FOUND / DOWN
                     │        (never PASS or FAIL — that is not this layer's job)
                     ▼
             ★ RULE ENGINE    Pure function. No LLM. No I/O. Same input → same output.
                     │        government value resolved before the claimed value
                     ▼
              SCORE + CITE    Weighted 0–100 risk · 1 Evidence row per Finding, always
                     │
                     ▼
          MATRIX · PDF REPORT · APPEND-ONLY AUDIT TRAIL
```

### Where the system refuses to guess

Four situations produce **NEEDS-REVIEW** instead of a verdict:

- The tender threshold was never extracted → nothing is known about the bar.
- No source produced the fact → absence of evidence isn't evidence of ineligibility.
- **The bid states two different values on two pages** → the contradiction *is* the signal.
- The comparison isn't evaluable → a data problem, not a vendor problem.

**Put on the slide:** the pipeline diagram — big, centred, with the RULE ENGINE box highlighted and
labelled "no LLM here". Push the tech table to a corner or the appendix if space is tight.

*Speaker notes:* If a judge asks "why not just ask GPT?" — point at the two boxes. Extraction is
where a model is allowed to be creative; the verdict box is a pure function you can unit-test. That
separation is the whole idea.

---

## SLIDE 4 — Feasibility and Viability

### Feasibility — this is built, not proposed

- Working end-to-end today: upload → ingest → extract → verify → compliance → report → audit.
- **95 automated backend tests, all passing.**
- Runs on a laptop: local LLM, SQLite, mock portals — **no internet, no cloud bill, no GPU cluster**.
- Rule packs are YAML: a procurement officer changes a turnover threshold without a developer.
- Adding a portal = one adapter file + one registry line.

### Challenges and risks → how we handle each

| Risk | Our strategy |
|---|---|
| **LLM hallucinates a requirement or a claim** | Four guardrails; an ungrounded snippet never reaches the database, and the model is excluded from the decision path entirely |
| **Government portals are down / rate-limited / captcha'd** | Adapters degrade to `DOWN`, findings become NEEDS-REVIEW; results are cached with a TTL so we never hammer a portal |
| **Scanned, skewed, poor-quality bids** | OCR fallback with deskew + denoise; below-threshold confidence is flagged for the officer, not silently trusted |
| **Numbers written a dozen ways** | A single normalization boundary — the engine only ever compares typed values |
| **Ambiguous legal clauses** | Fixed taxonomy with an explicit `manual_review` bucket; anything unmatched appears on the matrix as a zero-weight NEEDS-REVIEW rather than being force-fitted |
| **A verdict is legally challenged** | Every finding is stamped with the rule pack's SHA-256 and the engine version, so the decision stays re-derivable months later |
| **Sensitive bid documents** *(open gap — stated honestly)* | Auth is the next milestone: JWT + role-based access, department scoping, encrypted storage. Today it is a single-officer prototype |

**Put on the slide:** the risk → mitigation table. It is the most judge-friendly artefact in the deck
because it shows you know where your own system is weak.

*Speaker notes:* Say the auth gap out loud before a judge finds it. "It's a working prototype, not yet
a deployed service — authentication is the next milestone and the design is written down." Volunteered
honesty reads as engineering maturity; a discovered gap reads as overclaiming.

---

## SLIDE 5 — Impact and Benefits

### Impact on the target audience

| Stakeholder | Before | After |
|---|---|---|
| **Procurement officer** | Days per tender; personally accountable for checks they couldn't finish | Minutes to review a matrix; every row already verified and cited |
| **Buying department** | Awards on unverified eligibility | Overstated claims caught **before** award |
| **Honest vendors** | Lose to bidders who inflated turnover and were never checked | Compete on a level field |
| **Audit / vigilance** | Personal notes, not a record | Page-level evidence + an append-only trail |
| **Public exchequer** | Pays for work awarded to under-qualified suppliers | Fewer capability failures after award |

### Benefits

- **Social** — procurement decisions become explainable and challengeable; less discretion, more record.
- **Economic** — officer time redirected from lookups to judgement; fewer failed contracts and re-tenders.
- **Governance** — reproducible verdicts: the same documents always produce the same result, so two
  officers cannot reach different conclusions on identical facts.
- **Operational** — zero cloud dependency; deployable inside a department's own network, with bid
  documents never leaving it.
- **Environmental** — a paperless verification trail replaces printed comparison files.

> **Honesty note for the deck:** the "~80% less verification effort" figure is a **target, not a
> measured result** — we have no benchmark yet. Say "target" if you use the number at all. The
> measurement we plan: time an officer on *n* bids manually, then on the same set with TenderGuard,
> and publish both the time saved **and** the verdict disagreements.

**Put on the slide:** the before/after table. One number in large type — "216 manual comparisons →
1 upload" — is stronger than a paragraph.

*Speaker notes:* Do not quote a saving you have not measured. If asked for numbers, say what the
benchmark will be and that you would publish the disagreements too. Judges trust a team that shows
its measurement plan more than one that quotes a round figure.

---

## SLIDE 6 — Research and References

- **Problem source:** SIH26100 — AI Tender & Vendor Compliance Verification.
- **Procurement context:** GeM and CPPP handle bid *submission and workflow*, not the semantic
  verification of a claim against a government record — that comparison is still manual today.
- **Verification sources:** GST registration status (GSTN), Udyam / MSME registration, government
  debarment and blacklist listings.
- **Determinism in decision systems:** verdicts from an officer-editable YAML rule pack, versioned
  and hashed per decision, rather than from model output.
- **Grounding / anti-hallucination:** verbatim-span verification — an extraction whose quoted snippet
  is not literally present in the source page is rejected.
- **Document AI:** PyMuPDF (text + layout extraction) · Tesseract OCR with OpenCV preprocessing
  (deskew, denoise, adaptive threshold).
- **Retrieval:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim) with FAISS similarity search.
- **Project repository / docs:** `problem.md`, `solution.md`, `readme0111.md`, `docs/architecture.md`,
  `docs/rule_pack_spec.md`, `docs/api.md`.

*Speaker notes:* Add live URLs for the GST and Udyam portals and your repo link before submitting —
the SIH template expects clickable references.

---

# Appendix A — The 3-minute pitch

| Time | Say |
|---|---|
| 0:00–0:30 | **The problem.** One tender, eight bidders, twenty-seven criteria — 216 manual comparisons and dozens of portal lookups. It takes days, and the step that gets skipped is the one that matters: checking the claim against the government record. |
| 0:30–1:00 | **Why AI alone makes it worse.** An LLM that reads *and decides* is non-deterministic, can't cite, and hallucinates — the three properties least acceptable in a procurement audit. |
| 1:00–1:30 | **Our rule.** The LLM extracts; it never decides. Every verdict comes from a pure function over an officer-editable YAML rule pack. Same documents, same verdict, every time. |
| 1:30–2:15 | **The demo.** Upload tender + bid → matrix appears → open the FAILed turnover row: the bid claims ₹6.2 crore, the GST record says ₹4.1. Both shown, page cited, snippet quoted. → Download the PDF report. |
| 2:15–2:45 | **When things go wrong.** Portal down → NEEDS-REVIEW, never a false PASS. Scanned page → OCR with a low-confidence flag. Bid contradicts itself across pages → escalated to a human. |
| 2:45–3:00 | **Where we are.** Working end to end, 95 tests passing, runs entirely offline. Next milestone is authentication — until then it is a prototype, not a deployment. |

---

# Appendix B — Hard questions judges ask, and the answers

| Question | Answer |
|---|---|
| *"Isn't this just ChatGPT over a PDF?"* | No — a chatbot both reads and decides. We put the model on one side of a hard line: it produces snippet-backed facts, and a pure function produces the verdict. Run it twice, get the same answer; that is what an audit needs. |
| *"What if the LLM makes something up?"* | Any extraction whose quoted snippet isn't literally on that page is rejected before it reaches the database. And even a perfect extraction is only ever an *input* to a rule — never a verdict. |
| *"What if the GST portal is down?"* | The adapter returns `DOWN`, the finding becomes NEEDS-REVIEW and goes to a human. We never convert an outage into a PASS or a FAIL. |
| *"How does an officer change a criterion?"* | Edit the YAML rule pack — no code. The loader validates it and reports the offending rule *and the line number* if it's wrong. |
| *"How do you prove a verdict later?"* | Each finding stores the page, the verbatim snippet, the document's SHA-256, the rule pack's SHA-256 and version, and the engine version — plus an append-only audit row of who ran it and when. |
| *"Is our bid data safe?"* | The model runs locally via Ollama; nothing leaves the machine. Access control is the honest gap — JWT auth, role-based access and encryption at rest are the next milestone, and the design is written down. |
| *"Does it work at scale — eight bidders, not one?"* | Today it answers one bid at a time. Multi-bid comparison is a pure read-side aggregation over findings we already persist — it is the next feature after auth, and it needs no change to the decision logic. |
| *"What's your accuracy?"* | Extraction is guarded by verbatim grounding, so the failure mode is a *missed* fact, not a wrong one. The decision layer is deterministic and unit-tested — 95 tests. What we have not yet measured is officer time saved; we won't quote a number we haven't benchmarked. |

---

# Appendix C — Demo checklist (run before you present)

```bash
# from backend/
.venv/Scripts/python.exe -m pytest -q          # expect: 95 passed
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# from the project root
python scripts/generate_sample_pdfs.py         # sample tender + bid PDFs (once)
python scripts/load_sample_data.py             # seed → verify → compliance
python scripts/run_pipeline_cli.py             # end-to-end JSON findings, no UI needed
```

- [ ] `VERIFICATION_MODE=mock` — confirm the whole demo runs with **WiFi switched off**.
- [ ] Ollama is running locally (`ollama serve`) and the model is pulled.
- [ ] The seeded bid produces at least one **FAIL** with a visible claimed-vs-verified mismatch.
- [ ] The evidence viewer opens on the cited page for that finding.
- [ ] The PDF report downloads and shows both document hashes and the rule pack SHA-256.
- [ ] Have a fallback screen recording ready — never demo live without one.

---

# Appendix D — Slide design rules

- **Six slides. Do not add more** — the SIH template is fixed and judges score against it.
- One idea per slide; the bullets above are already trimmed to slide length.
- Diagram > paragraph. Slide 3 should be mostly the pipeline picture.
- Highlight the **rule engine box** in a different colour on the pipeline and label it "no LLM here" —
  that one visual carries the entire USP.
- Use real screenshots (matrix, evidence viewer, PDF report), not stock illustrations.
- Keep the honesty notes (auth gap, unmeasured 80%) **in the speaker notes**, not on the slides — but
  say them out loud.
- Readable from the back of a hall: minimum 18pt body, 28pt headings.
