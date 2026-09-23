/* ==========================================================================
   data.js — content for the explainer.

   Everything here is transcribed from the repository, not invented:
     RULE_PACKS   <- backend/rules/default_{goods,works,services}.yaml
     MOCK_GST     <- data/mock_portals/gst.json
     MOCK_UDYAM   <- data/mock_portals/udyam.json
     MOCK_DEBAR   <- data/mock_portals/debarment.json
     PAGE_TEXT    <- scripts/generate_sample_pdfs.py (the tender it writes)
   If any of those files change, change these to match.
   ========================================================================== */

(function (global) {
  'use strict';

  /* ------------------------------------------------------------------ */
  /* Rule packs — backend/rules/*.yaml                                    */
  /* ------------------------------------------------------------------ */

  var RULE_PACKS = {
    goods: {
      key: 'goods',
      version: 1,
      name: 'Default Goods Procurement Pack',
      file: 'backend/rules/default_goods.yaml',
      rules: [
        { id: 'REQ-TURNOVER', label: 'Minimum average annual turnover', severity: 'CRITICAL', weight: 25,
          fact: 'financials.avg_annual_turnover', operator: 'gte',
          source_priority: ['government', 'document'], threshold_from: 'tender.turnover_requirement' },
        { id: 'REQ-GST-ACTIVE', label: 'GST registration must be active', severity: 'CRITICAL', weight: 20,
          fact: 'gst.status', operator: 'eq', value: 'ACTIVE', source_priority: ['government'] },
        { id: 'REQ-MSME', label: 'Udyam certificate valid if claiming MSME benefit', severity: 'MAJOR', weight: 10,
          fact: 'udyam.valid', operator: 'eq', value: true, applies_if: 'bid.claims_msme_benefit == true' },
        { id: 'REQ-DEBARMENT', label: 'Vendor must not be debarred / blacklisted', severity: 'BLOCKER', weight: 40,
          fact: 'debarment.listed', operator: 'eq', value: false, source_priority: ['government'] },
        { id: 'REQ-EXPERIENCE', label: 'Minimum years of relevant experience', severity: 'MAJOR', weight: 15,
          fact: 'experience.years', operator: 'gte',
          source_priority: ['document'], threshold_from: 'tender.experience_requirement' },
        { id: 'REQ-PAN', label: 'PAN must be present and well-formed', severity: 'MINOR', weight: 5,
          fact: 'identity.pan', operator: 'regex', value: '^[A-Z]{5}[0-9]{4}[A-Z]$', source_priority: ['document'] }
      ]
    },
    works: {
      key: 'works',
      version: 1,
      name: 'Default Works (Construction) Procurement Pack',
      file: 'backend/rules/default_works.yaml',
      rules: [
        { id: 'REQ-TURNOVER', label: 'Minimum average annual turnover', severity: 'CRITICAL', weight: 20,
          fact: 'financials.avg_annual_turnover', operator: 'gte',
          source_priority: ['government', 'document'], threshold_from: 'tender.turnover_requirement' },
        { id: 'REQ-GST-ACTIVE', label: 'GST registration must be active', severity: 'CRITICAL', weight: 15,
          fact: 'gst.status', operator: 'eq', value: 'ACTIVE', source_priority: ['government'] },
        { id: 'REQ-SIMILAR-WORK-VALUE', label: 'Minimum value of similar completed works', severity: 'CRITICAL', weight: 25,
          fact: 'experience.similar_work_value', operator: 'gte',
          source_priority: ['document'], threshold_from: 'tender.similar_work_value_requirement' },
        { id: 'REQ-EMD', label: 'Earnest Money Deposit submitted', severity: 'BLOCKER', weight: 15,
          fact: 'financials.emd_submitted', operator: 'eq', value: true, source_priority: ['document'] },
        { id: 'REQ-MSME', label: 'Udyam certificate valid if claiming MSME benefit', severity: 'MAJOR', weight: 10,
          fact: 'udyam.valid', operator: 'eq', value: true, applies_if: 'bid.claims_msme_benefit == true' },
        { id: 'REQ-DEBARMENT', label: 'Vendor must not be debarred / blacklisted', severity: 'BLOCKER', weight: 40,
          fact: 'debarment.listed', operator: 'eq', value: false, source_priority: ['government'] }
      ]
    },
    services: {
      key: 'services',
      version: 1,
      name: 'Default Services Procurement Pack',
      file: 'backend/rules/default_services.yaml',
      rules: [
        { id: 'REQ-TURNOVER', label: 'Minimum average annual turnover', severity: 'CRITICAL', weight: 20,
          fact: 'financials.avg_annual_turnover', operator: 'gte',
          source_priority: ['government', 'document'], threshold_from: 'tender.turnover_requirement' },
        { id: 'REQ-GST-ACTIVE', label: 'GST registration must be active', severity: 'CRITICAL', weight: 15,
          fact: 'gst.status', operator: 'eq', value: 'ACTIVE', source_priority: ['government'] },
        { id: 'REQ-EXPERIENCE', label: 'Minimum years of relevant service delivery experience', severity: 'MAJOR', weight: 20,
          fact: 'experience.years', operator: 'gte',
          source_priority: ['document'], threshold_from: 'tender.experience_requirement' },
        { id: 'REQ-CERTIFICATION', label: 'Required quality certification held (e.g. ISO)', severity: 'MAJOR', weight: 10,
          fact: 'certification.iso_certified', operator: 'eq', value: true, source_priority: ['document'] },
        { id: 'REQ-MSME', label: 'Udyam certificate valid if claiming MSME benefit', severity: 'MAJOR', weight: 10,
          fact: 'udyam.valid', operator: 'eq', value: true, applies_if: 'bid.claims_msme_benefit == true' },
        { id: 'REQ-DEBARMENT', label: 'Vendor must not be debarred / blacklisted', severity: 'BLOCKER', weight: 40,
          fact: 'debarment.listed', operator: 'eq', value: false, source_priority: ['government'] }
      ]
    }
  };

  /* ------------------------------------------------------------------ */
  /* Mock portal fixtures — data/mock_portals/*.json                      */
  /* ------------------------------------------------------------------ */

  var MOCK_GST = {
    '27AAAPL1234C1Z5': { status: 'ACTIVE', legal_name: 'Ganga Infra Projects Pvt Ltd',
      registration_date: '2018-04-01', filing_status: 'REGULAR', avg_annual_turnover: 41000000 },
    '07BBCPL5678D1Z2': { status: 'ACTIVE', legal_name: 'Bharat Steelworks Ltd',
      registration_date: '2015-09-12', filing_status: 'REGULAR', avg_annual_turnover: 92000000 },
    '29CCDPL9012E1Z8': { status: 'CANCELLED', legal_name: 'Southern Traders & Co',
      registration_date: '2012-03-20', cancellation_date: '2024-11-05', filing_status: 'SUSPENDED',
      avg_annual_turnover: 18000000 }
  };

  var MOCK_UDYAM = {
    'UDYAM-DL-01-1234567': { valid: true, enterprise_name: 'Ganga Infra Projects Pvt Ltd', category: 'Small' },
    'UDYAM-MH-05-7654321': { valid: true, enterprise_name: 'Bharat Steelworks Ltd', category: 'Medium' }
  };

  var MOCK_DEBARMENT = { listed_gstins: ['29CCDPL9012E1Z8'], listed_pans: [] };

  /* Vendor presets for the bench — the three real fixtures, plus the two
     ways a portal can fail to give an answer. */
  var VENDORS = [
    { key: 'ganga',   label: 'Ganga Infra Projects Pvt Ltd', gstin: '27AAAPL1234C1Z5', pan: 'AAAPL1234C',
      udyam: 'UDYAM-DL-01-1234567', portal: 'UP',
      note: 'The demo vendor. GST-verified turnover is 4.1 Cr — lower than what the bid claims.' },
    { key: 'bharat',  label: 'Bharat Steelworks Ltd', gstin: '07BBCPL5678D1Z2', pan: 'BBCPL5678D',
      udyam: 'UDYAM-MH-05-7654321', portal: 'UP',
      note: 'Comfortably qualified: GST ACTIVE, 9.2 Cr turnover, not debarred.' },
    { key: 'southern', label: 'Southern Traders & Co', gstin: '29CCDPL9012E1Z8', pan: 'CCDPL9012E',
      udyam: '', portal: 'UP',
      note: 'GST registration CANCELLED and on the debarment list — two BLOCKER-adjacent problems.' },
    { key: 'unknown', label: 'Vendor with no GST record', gstin: '27ZZZZZ9999Z1Z9', pan: 'ZZZZZ9999Z',
      udyam: '', portal: 'NOT_FOUND',
      note: 'Portal reached, no record found. status=NOT_FOUND — no facts, so the rules that need them go to review.' },
    { key: 'down',    label: 'GST portal unreachable', gstin: '27AAAPL1234C1Z5', pan: 'AAAPL1234C',
      udyam: 'UDYAM-DL-01-1234567', portal: 'DOWN',
      note: 'The adapter returns DOWN instead of raising. No verified facts reach the engine — never a false PASS.' }
  ];

  /* ------------------------------------------------------------------ */
  /* 03 — the seven stages                                                */
  /* ------------------------------------------------------------------ */

  var STAGES = [
    {
      n: '01', key: 'Ingestion', path: 'services/ingestion/',
      inp: 'An uploaded PDF (multipart, 50 MB ceiling)',
      out: 'One Document row + one DocumentPage row per page',
      does: [
        "Checks extension, content type and size, and rejects zero-byte files.",
        "Hashes the bytes with SHA-256. If that hash already exists <em>for the same kind</em>, the existing row is reused and the response says <span class='k'>duplicate: true</span> — no re-storing, no re-processing.",
        "PyMuPDF pulls per-page text plus <em>word-level bounding boxes</em>.",
        "Any page with under 50 characters of embedded text goes to OCR — OpenCV deskew and denoise, then Tesseract — and is flagged <span class='k'>low_confidence</span> rather than silently trusted.",
        "<span class='k'>layout.py</span> detects headings and tables, so the eligibility section can be found and chunked around."
      ],
      files: ['upload.py', 'hashing.py', 'pdf_loader.py', 'ocr.py', 'layout.py', 'pipeline.py', 'enqueue.py'],
      why: "The bounding boxes are captured here, at the only moment they exist, because everything downstream promises to point at a sentence on a page. And the upload returns instantly with a job_id: enqueue.py probes whether Redis is actually reachable and runs the ingest inline if it isn't. The upload always completes — sync or async."
    },
    {
      n: '02', key: 'Extraction', path: 'services/extraction/ · services/llm/', llm: true,
      inp: 'DocumentPage rows',
      out: 'Requirement rows (tender side) or ClaimedFact rows (bid side) — typed value + page + snippet',
      does: [
        "One Ollama call per page, temperature 0 with a pinned seed, JSON mode forced.",
        "The response is validated against a Pydantic schema. On failure the model gets its own bad output, the error and the schema back, and is asked to fix it — up to two repairs, then it raises.",
        "Every item must carry a verbatim source snippet. <span class='k'>snippet_guard.py</span> rejects anything whose snippet isn't literally on that page.",
        "Survivors pass through the normalizers: \"Rs. 6,20,00,000\" becomes <span class='k'>62000000.0</span>.",
        "Persisted idempotently per <span class='k'>(fact_key, page, snippet)</span> — re-running doesn't duplicate rows."
      ],
      files: ['tender_requirements.py', 'vendor_facts.py', 'snippet_guard.py', 'normalizers.py', 'fact_normalization.py', 'llm/json_guard.py', 'llm/client.py', 'llm/prompts/'],
      why: "This is the only non-deterministic band in the system, so it is fenced on four sides — see section 07. Extracted tender requirements are also matched against the rule pack by category and keyword; a confident match sets external_ref to the rule id, and an unmatched one surfaces later as a MANUAL_CHECK finding at zero weight."
    },
    {
      n: '03', key: 'Verification', path: 'services/verification/',
      inp: "The vendor's GSTIN, PAN and Udyam number",
      out: 'A VerificationResult per portal, with a normalized dict of fact keys',
      does: [
        "One <span class='k'>PortalAdapter</span> per portal behind a registry switched by <span class='k'>VERIFICATION_MODE</span>.",
        "<span class='k'>mock</span> reads JSON fixtures from <span class='k'>data/mock_portals/</span> — the entire demo runs with the network off. <span class='k'>live</span> hits the real APIs.",
        "An adapter returns <span class='k'>UP</span>, <span class='k'>NOT_FOUND</span> or <span class='k'>DOWN</span>. Never PASS, never FAIL.",
        "Results are cached per <span class='k'>(bid, portal)</span> for <span class='k'>VERIFICATION_CACHE_TTL_SECONDS</span>.",
        "Normalized keys are the vocabulary rules speak: <span class='k'>gst.status</span>, <span class='k'>financials.avg_annual_turnover</span>, <span class='k'>udyam.valid</span>, <span class='k'>debarment.listed</span>."
      ],
      files: ['base.py', 'registry.py', 'cache.py', 'adapters/gst.py', 'adapters/udyam.py', 'adapters/mock_portal.py'],
      why: "A government portal being unreachable must never produce a verdict. DOWN means the engine finds no value for that fact and reports NEEDS_REVIEW — a human looks at it. An adapter that raised, or that guessed, would put a false PASS into a procurement record."
    },
    {
      n: '04', key: 'Rules', path: 'services/rules/',
      inp: 'A rule pack + three dicts: claimed, verified, context',
      out: 'A list of findings — status, reason, expected, claimed, verified, risk_contribution',
      does: [
        "Skip the rule entirely if <span class='k'>applies_if</span> evaluates false — no finding, no weight.",
        "Resolve the <em>expected</em> value: either a literal <span class='k'>value</span>, or a <span class='k'>threshold_from</span> lookup in context. A missing context key means NEEDS_REVIEW, not a guess.",
        "Resolve the <em>actual</em> value by walking <span class='k'>source_priority</span> in order — government facts live in <span class='k'>verified</span>, document facts in <span class='k'>claimed</span>.",
        "If the bid stated two different values for the same fact on different pages, the contradiction itself forces NEEDS_REVIEW — it is never resolved by last-write-wins.",
        "Evaluate with one operator from a fixed set of ten: gte, lte, gt, lt, eq, in, regex, date_before, date_after, exists."
      ],
      files: ['loader.py', 'engine.py', 'operators.py', 'condition.py'],
      why: "evaluate_rule_pack() is a pure function. No LLM, no database, no clock, no network. Feed it the same pack, facts and context and it returns the same findings forever — that is what converts an unciteable chatbot answer into a procurement record that survives a challenge. applies_if is parsed by a tiny hand-written grammar, never eval(), because rule packs are officer-editable data."
    },
    {
      n: '05', key: 'Risk', path: 'services/risk/scorer.py',
      inp: 'The list of findings',
      out: 'score, band, forced_by_blocker, and the pass/fail/review counts',
      does: [
        "<span class='k'>score = Σ risk_contribution ÷ Σ weight × 100</span>.",
        "PASS contributes 0. FAIL contributes the rule's full weight. NEEDS_REVIEW contributes half.",
        "Bands: ≤33 LOW, ≤65 MEDIUM, &gt;65 HIGH.",
        "A FAILed <span class='k'>BLOCKER</span> rule forces the HIGH band regardless of the arithmetic."
      ],
      files: ['scorer.py'],
      why: "One disqualifying fact — the vendor is debarred — should never be diluted by twenty-six unrelated passes. So it isn't averaged in, it overrides. Section 06 lets you play with the actual formula."
    },
    {
      n: '06', key: 'Compliance', path: 'services/compliance/service.py',
      inp: 'A bid id',
      out: 'Finding + Evidence rows, and the risk assessment',
      does: [
        "Builds <span class='k'>claimed</span> from the bid's ClaimedFact rows, surfacing cross-page contradictions as <span class='k'>conflicts</span>.",
        "Builds <span class='k'>verified</span> by running verification-with-cache for every portal the vendor has an identifier for.",
        "Builds <span class='k'>context</span> from the tender's requirements — thresholds, and <span class='k'>bid.claims_msme_benefit</span>.",
        "Runs the engine, scores the findings, then <em>replaces</em> this bid's findings rather than appending.",
        "Writes exactly one Evidence row per Finding, stamped with the rule pack's name, version and SHA-256, and the engine version."
      ],
      files: ['service.py', 'requirement_binding.py'],
      why: "This is the only place that knows about both the database and the engine — which is precisely why the engine stays pure. Replace-not-append because the engine is deterministic: a history of identical runs is noise, and the matrix should show current truth."
    },
    {
      n: '07', key: 'Report &amp; audit', path: 'services/reports/ · services/audit/',
      inp: 'The last compliance run',
      out: 'A PDF, and one append-only audit row per action',
      does: [
        "ReportLab renders the summary, the full compliance matrix, and an evidence appendix quoting the exact snippet behind every non-PASS finding.",
        "Both documents' SHA-256 hashes are stamped into the report.",
        "<span class='k'>audit/trail.py</span> appends a row for every upload, verification run, compliance run, requirement edit and report download.",
        "The actor comes from the <span class='k'>X-Actor</span> header, defaulting to <span class='k'>\"officer\"</span>."
      ],
      files: ['pdf_builder.py', 'trail.py'],
      why: "The deliverable was never a score. It's a document an officer can attach to a file and defend a year later — which is why the hashes are in it. There is no real auth yet; X-Actor is a placeholder for it, and the audit trail is built to accept a real identity the day one exists."
    }
  ];

  /* ------------------------------------------------------------------ */
  /* 04 — the trace                                                       */
  /* ------------------------------------------------------------------ */

  var TRACE = [
    {
      h: 'The tender says what is required',
      p: 'Ingestion turns the tender PDF into pages. Extraction reads page 2 and produces one Requirement, carrying the sentence it came from.',
      q: 'tender.pdf · page 2\n"3.1 The bidder must have an average annual turnover of at least\n Rs. 5 Crore in each of the last 3 financial years."',
      k: 'Requirement.expected.value = <span class="val hi">50000000.0</span>  →  context key <span class="val">tender.turnover_requirement</span>'
    },
    {
      h: 'The bid states what the vendor claims',
      p: 'Same treatment on the bid PDF. The claim becomes a typed ClaimedFact, page-cited, normalized from Indian currency prose to a plain float.',
      q: 'bid.pdf · page 2\n"Average annual turnover for the last 3 financial years\n is Rs. 6,20,00,000."',
      k: 'ClaimedFact <span class="val">financials.avg_annual_turnover</span> = <span class="val hi">62000000.0</span>  ·  page 2'
    },
    {
      h: 'The government record is fetched',
      p: 'The vendor gave a GSTIN, so the GST adapter runs. It returns UP with a normalized dict — and it makes no judgement about any of it.',
      q: 'GST · GSTIN 27AAAPL1234C1Z5 · status UP\n{ "gst.status": "ACTIVE",\n  "gst.legal_name": "Ganga Infra Projects Pvt Ltd",\n  "financials.avg_annual_turnover": 41000000 }',
      k: 'verified[<span class="val">financials.avg_annual_turnover</span>] = <span class="val hi">41000000</span>'
    },
    {
      h: 'The rule is loaded',
      p: 'REQ-TURNOVER, from the goods rule pack. Note that it does not carry a threshold of its own — it reads one from the tender.',
      q: '- id: REQ-TURNOVER\n  severity: CRITICAL\n  weight: 25\n  fact: financials.avg_annual_turnover\n  operator: gte\n  threshold_from: tender.turnover_requirement\n  source_priority: [government, document]',
      k: 'expected = context["tender.turnover_requirement"] = <span class="val hi">50000000.0</span>'
    },
    {
      h: 'The engine chooses which number to judge',
      p: 'It walks source_priority in order. "government" maps to the verified bucket, which has the key — so the search stops there. The claimed 6.2 Cr is never used as the actual value.',
      q: 'source_priority: [government, document]\n  government → verified["financials.avg_annual_turnover"] → 41000000  ✓ stop\n  document   → (never reached)',
      k: 'actual = <span class="val hi">41000000</span>   ·   claimed <span class="val strike">62000000</span> is kept on the finding, not used as the value'
    },
    {
      h: 'One operator runs',
      p: 'gte, from the fixed set of ten. No model, no network, no clock — just a comparison.',
      q: 'op_gte(41000000, 50000000)  →  False',
      k: 'status = <span class="chip fail">FAIL</span>   risk_contribution = weight = <span class="val hi">25</span>'
    },
    {
      h: 'The verdict is filed with its proof',
      p: 'One Evidence row is written alongside the finding: the bid document, the page, the exact snippet, and the document’s SHA-256. The finding also records which rule pack and engine version produced it.',
      q: 'Finding  REQ-TURNOVER  FAIL  weight 25  severity CRITICAL\n  expected  { operator: "gte", value: 50000000.0 }\n  verified  { value: 41000000, source: { portal: "GST", fetched_at: ... } }\n  claimed   { value: 62000000.0, source: { page: 2, snippet: "..." } }\nEvidence  bid.pdf · page 2 · sha256 ... · snippet "Average annual turnover ..."',
      k: '"The vendor claimed 6.2 Cr. GST says 4.1 Cr. The tender needs 5 Cr. Here is the page."'
    }
  ];

  /* ------------------------------------------------------------------ */
  /* 05 — YAML annotator                                                  */
  /* ------------------------------------------------------------------ */

  var FIELD_NOTES = {
    version: ['version', 'Informational for now. Bumping it does not change behaviour — but it is stamped onto every finding the pack produces, so you can tell which pack version filed which verdict.'],
    name: ['name', 'Human-readable pack name. Also stamped onto findings, alongside the pack file’s SHA-256.'],
    id: ['id', 'Unique within the pack. This string is the link between three things: the rule, the Requirement row an officer sees (matched by external_ref), and the row in the compliance matrix.'],
    label: ['label', 'What the officer reads in the matrix. Also the text used if the system has to synthesize a Requirement row because extraction never produced one.'],
    severity: ['severity', 'BLOCKER · CRITICAL · MAJOR · MINOR. Only BLOCKER changes the arithmetic: a FAILed BLOCKER forces the risk band to HIGH no matter what the score says. The other three are for the human reading the matrix.'],
    weight: ['weight', 'How much this rule contributes to the 0–100 risk score. A FAIL contributes the full weight, a NEEDS_REVIEW contributes half, a PASS contributes nothing. Skipped rules leave the denominator entirely.'],
    fact: ['fact', 'The dotted key this rule reads. It must match a key that either a vendor-fact extraction or a verification adapter actually produces — that shared vocabulary is what lets a YAML file address a value pulled out of a PDF.'],
    operator: ['operator', 'One of exactly ten: gte, lte, gt, lt, eq, in, regex, date_before, date_after, exists. A fixed set, not an expression language — you cannot write arbitrary logic into a rule pack, which is the point.'],
    value: ['value', 'A literal expected value. Used when the tender does not supply the threshold — "GST must be ACTIVE" is true of every tender, so it is written here rather than read from context.'],
    threshold_from: ['threshold_from', 'A context key whose value becomes the expected value instead of a literal. This is how one rule serves every tender: the turnover bar comes from the tender being evaluated. If the key is missing from context, the finding becomes NEEDS_REVIEW — never a guessed PASS or FAIL.'],
    source_priority: ['source_priority', 'Ordered. "government" reads the verified bucket, "document" reads the claimed bucket, and the engine takes the first source that actually has the fact. Listing government first is the single line that catches an inflated claim — see section 04. Defaults to [document] if omitted.'],
    applies_if: ['applies_if', 'A tiny <span class="k">&lt;fact.path&gt; &lt;op&gt; &lt;literal&gt;</span> condition. If it evaluates false the rule is skipped entirely — no finding is produced and its weight leaves the score. Parsed by a hand-written grammar in condition.py, never eval(), because rule packs are officer-editable data files.']
  };

  /* Token stream for the annotated YAML view.
     '@x' = clickable field name · '#x' = rule id · '%x' = comment · else literal */
  var YAML_SRC = [
    ['@version', ': 1'],
    ['@name', ': Default Goods Procurement Pack'],
    ['rules:', ''],
    ['  - ', '@id', ': ', '#REQ-TURNOVER'],
    ['    ', '@label', ': Minimum average annual turnover'],
    ['    ', '@severity', ': CRITICAL'],
    ['    ', '@weight', ': 25'],
    ['    ', '@fact', ': financials.avg_annual_turnover'],
    ['    ', '@operator', ': gte'],
    ['    ', '@source_priority', ': [government, document]   ', '%# govt value beats claimed value'],
    ['    ', '@threshold_from', ': tender.turnover_requirement'],
    ['', ''],
    ['  - ', '@id', ': ', '#REQ-GST-ACTIVE'],
    ['    ', '@label', ': GST registration must be active'],
    ['    ', '@severity', ': CRITICAL'],
    ['    ', '@weight', ': 20'],
    ['    ', '@fact', ': gst.status'],
    ['    ', '@operator', ': eq'],
    ['    ', '@value', ': ACTIVE'],
    ['    ', '@source_priority', ': [government]'],
    ['', ''],
    ['  - ', '@id', ': ', '#REQ-MSME'],
    ['    ', '@label', ': Udyam certificate valid if claiming MSME benefit'],
    ['    ', '@severity', ': MAJOR'],
    ['    ', '@weight', ': 10'],
    ['    ', '@fact', ': udyam.valid'],
    ['    ', '@operator', ': eq'],
    ['    ', '@value', ': true'],
    ['    ', '@applies_if', ': bid.claims_msme_benefit == true'],
    ['', ''],
    ['  - ', '@id', ': ', '#REQ-DEBARMENT'],
    ['    ', '@label', ': Vendor must not be debarred / blacklisted'],
    ['    ', '@severity', ': BLOCKER'],
    ['    ', '@weight', ': 40'],
    ['    ', '@fact', ': debarment.listed'],
    ['    ', '@operator', ': eq'],
    ['    ', '@value', ': false'],
    ['    ', '@source_priority', ': [government]'],
    ['', ''],
    ['  - ', '@id', ': ', '#REQ-EXPERIENCE'],
    ['    ', '@label', ': Minimum years of relevant experience'],
    ['    ', '@severity', ': MAJOR'],
    ['    ', '@weight', ': 15'],
    ['    ', '@fact', ': experience.years'],
    ['    ', '@operator', ': gte'],
    ['    ', '@source_priority', ': [document]'],
    ['    ', '@threshold_from', ': tender.experience_requirement'],
    ['', ''],
    ['  - ', '@id', ': ', '#REQ-PAN'],
    ['    ', '@label', ': PAN must be present and well-formed'],
    ['    ', '@severity', ': MINOR'],
    ['    ', '@weight', ': 5'],
    ['    ', '@fact', ': identity.pan'],
    ['    ', '@operator', ': regex'],
    ['    ', '@value', ': "^[A-Z]{5}[0-9]{4}[A-Z]$"'],
    ['    ', '@source_priority', ': [document]']
  ];

  /* ------------------------------------------------------------------ */
  /* 07 — snippet guard                                                   */
  /* ------------------------------------------------------------------ */

  /* Exactly the page-2 text scripts/generate_sample_pdfs.py writes. */
  var PAGE_TEXT =
    "3. Eligibility Criteria\n" +
    "3.1 The bidder must have an average annual turnover of at least Rs. 5 Crore\n" +
    "    in each of the last 3 financial years.\n" +
    "3.2 The bidder must hold a valid and active GST registration.\n" +
    "3.3 The bidder must have a minimum of 5 years of relevant experience in\n" +
    "    similar road construction equipment supply contracts.\n" +
    "3.4 The bidder must not be currently debarred or blacklisted by any\n" +
    "    government department.\n" +
    "3.5 The bidder's PAN must be provided and correctly formatted.";

  var SNIPPETS = [
    { t: 'an average annual turnover of at least Rs. 5 Crore',
      why: 'Copied verbatim off the page. Kept, normalized to 50000000.0, and stored with page 2 as its citation.' },
    { t: 'must hold a valid and active GST registration',
      why: 'Verbatim again, across a line the model read correctly. Kept.' },
    { t: 'minimum average annual turnover of Rs. 5 crore',
      why: 'A fair, accurate paraphrase — and rejected. The page says "an average annual turnover of at least". The guard has no opinion about meaning; it only asks whether these characters are on that page. Bluntness is the feature: a guard that needed judgement could be argued with.' },
    { t: 'a minimum of 3 years of relevant experience',
      why: 'Rejected, and this is the one that matters. The tender says 5 years. A model that quietly drifted a number would have written a wrong threshold into a procurement record — the guard catches it because the sentence is not on the page.' },
    { t: 'The bidder must hold ISO 9001:2015 certification.',
      why: 'Rejected. Pure invention, plausible-sounding for a procurement document, nowhere in the text.' },
    { t: 'THE  BIDDER   MUST NOT BE currently debarred',
      why: 'Kept. Normalization collapses runs of whitespace and lowercases both sides before comparing, so formatting noise from the PDF does not cause a false rejection.' }
  ];

  /* Amount strings for the live normalizer demo (fence 4). */
  var AMOUNT_SAMPLES = [
    'Rs. 6,20,00,000',
    '6.2 Crore',
    '5cr',
    '₹50,00,000',
    '62 lakh',
    '50 million',
    '5,00,00,000/-',
    'about five crore'
  ];

  /* ------------------------------------------------------------------ */

  global.TGData = {
    RULE_PACKS: RULE_PACKS,
    MOCK_GST: MOCK_GST,
    MOCK_UDYAM: MOCK_UDYAM,
    MOCK_DEBARMENT: MOCK_DEBARMENT,
    VENDORS: VENDORS,
    STAGES: STAGES,
    TRACE: TRACE,
    FIELD_NOTES: FIELD_NOTES,
    YAML_SRC: YAML_SRC,
    PAGE_TEXT: PAGE_TEXT,
    SNIPPETS: SNIPPETS,
    AMOUNT_SAMPLES: AMOUNT_SAMPLES
  };
})(typeof window !== 'undefined' ? window : globalThis);
