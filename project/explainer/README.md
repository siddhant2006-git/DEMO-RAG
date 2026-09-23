# TenderGuard architecture explainer

A self-contained interactive website that explains this system's architecture, built for
onboarding a new developer and for walking a reviewer through the design decisions.

No build step, no dependencies, no npm install. Plain HTML, CSS and JavaScript.

## Run it

```bash
python explainer/serve.py          # http://localhost:8080, opens a browser
python explainer/serve.py 9000     # a different port
```

Opening `explainer/index.html` directly with `file://` also works — the scripts are classic
scripts, not ES modules.

## What's in it

Thirteen sections, readable top to bottom or jumpable from the index in the left rail.
Five of them are interactive:

| Section | What you can do |
|---|---|
| 03 · The seven stages | Click any pipeline stage for its inputs, outputs, real filenames, and why it's built that way |
| 04 · Follow one number | Step through ₹6.2 Cr claimed vs ₹4.1 Cr on the GST record; flip `source_priority` and watch the verdict flip |
| 05 · Rules are data | Click any field in the goods rule pack for what it does |
| 06 · Risk playground | Set each rule's outcome; the real weighted formula and the BLOCKER override run live |
| 07 · Fencing the model | Test the snippet guard and the currency normalizer against real page text |
| 08 · **The bench** | Pick a rule pack and a vendor, edit the claims and the tender thresholds, and get a full compliance matrix — findings, evidence, risk score |

## Files

```
explainer/
├─ index.html            the page — content and structure
├─ assets/
│  ├─ styles.css         design tokens, light + dark, print stylesheet
│  ├─ data.js            content transcribed from the repo (rule packs, fixtures, stage notes)
│  ├─ engine.js          a JS port of the decision layer — see below
│  └─ app.js             UI wiring only; no decision logic
├─ serve.py              stdlib static server
├─ parity_check.py       proves engine.js still agrees with the Python
└─ parity_runner.js      node half of the parity check
```

## `engine.js` is a port, not the engine

Section 08 runs a real rule evaluation in the browser. That code is a line-for-line
JavaScript translation of:

| `explainer/assets/engine.js` | mirrors |
|---|---|
| `OPERATORS`, `evaluate()` | `backend/app/services/rules/operators.py` |
| `evaluateCondition()` | `backend/app/services/rules/condition.py` |
| `evaluateRulePack()` | `backend/app/services/rules/engine.py` |
| `scoreFindings()` | `backend/app/services/risk/scorer.py` |
| `normalizeAmount()` and friends | `backend/app/services/extraction/normalizers.py` |
| `isSnippetGrounded()` | `backend/app/services/extraction/snippet_guard.py` |

The real engine runs in Python on the server and is the only thing that ever writes a
`Finding` row. **If the two disagree, the Python is right and the port is stale.**

`data.js` likewise transcribes `backend/rules/*.yaml` and `data/mock_portals/*.json`.

## Keeping it honest

```bash
backend/.venv/Scripts/python.exe explainer/parity_check.py
```

Runs the same scenarios through both implementations and diffs them — 39 checks covering
all three rule packs, eleven engine/scorer scenarios (including the blocker override,
cross-page conflicts, unresolvable thresholds and empty fact sets), sixteen
`normalize_amount` cases and nine snippet-guard cases. Exits non-zero on any mismatch.

Needs `node` on PATH. Run it after changing either `engine.js`/`data.js` or the Python
files they mirror.

## Editing

- **Content** (stage descriptions, the trace, field notes, snippets) → `assets/data.js`
- **Prose sections and diagrams** → `index.html`
- **Look** → `assets/styles.css`. Every colour is a token defined on `:root`; the two dark
  blocks redefine only tokens, so nothing is ever declared in one theme and missing in the
  other.
- **Behaviour** → `assets/app.js`. Keep decision logic out of it; that belongs in
  `engine.js` where the parity check can see it.

## Deploying

The site is static, so any static host serves it. Note that the repo's `vercel.json` builds
`frontend/` and is not set up to publish this folder — publishing it would need a separate
project or an added output path, which hasn't been done.
