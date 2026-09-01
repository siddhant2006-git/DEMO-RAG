# Rule pack spec

A rule pack is a YAML file under `backend/rules/` that defines the criteria a
bid is checked against for one tender category (`goods`, `works`, or
`services`). Rules are data, not code — an officer can add or edit one
without a developer touching Python.

## Top-level shape

```yaml
version: 1
name: Default Goods Procurement Pack
rules:
  - id: REQ-TURNOVER
    ...
```

- `version` — integer, informational for now.
- `name` — human-readable pack name.
- `rules` — list of rule objects (below).

## Rule fields

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Unique within the pack, e.g. `REQ-TURNOVER`. Shown in the compliance matrix and linked to the `Requirement` row an officer sees. |
| `label` | yes | Short human-readable description. |
| `severity` | yes | One of `BLOCKER`, `CRITICAL`, `MAJOR`, `MINOR`. A **FAILed BLOCKER** forces the bid's risk band to `HIGH` regardless of everything else. |
| `weight` | yes | Number contributing to the 0-100 risk score. A FAIL contributes the full weight; NEEDS-REVIEW contributes half. |
| `fact` | yes | Dotted key the rule reads, e.g. `financials.avg_annual_turnover`. Must match a key either a vendor fact extraction or a verification adapter produces. |
| `operator` | yes | One of `gte`, `lte`, `gt`, `lt`, `eq`, `in`, `regex`, `date_before`, `date_after`, `exists`. |
| `value` | one of `value`/`threshold_from` required (unless operator is `exists`) | A literal expected value, e.g. `ACTIVE`, `true`, a regex pattern. |
| `threshold_from` | see above | A context key whose value (usually a tender-specific number extracted from the tender text) is used as the expected value instead of a literal. |
| `source_priority` | no (default `[document]`) | Ordered list of `government` / `document`. The engine resolves `fact`'s actual value by trying each source in order — **government beats document** is expressed by listing `government` first. This is how a mismatch between a vendor's claim and a government record surfaces as the deciding value. |
| `applies_if` | no | A tiny `<fact.path> <op> <literal>` condition (e.g. `bid.claims_msme_benefit == true`). Rules whose condition evaluates false are skipped entirely — no finding is produced. Parsed with a fixed-grammar parser, never `eval()`, since rule packs are meant to be officer-editable. |

## Loading and validation

`backend/app/services/rules/loader.py` parses the YAML with a line-tracking
loader, so a malformed rule pack fails fast with a line number instead of a
generic error. Every rule is validated for required fields, a known
severity, and having either `value` or `threshold_from` (unless the operator
is `exists`).

## Evaluation

`backend/app/services/rules/engine.py` takes a loaded `RulePack` plus three
inputs and returns a list of findings — deterministically, with no LLM calls:

- `claimed: dict[str, FactValue]` — facts extracted from the bid document.
- `verified: dict[str, FactValue]` — facts returned by government portal
  adapters (see `backend/app/services/verification/`).
- `context: dict` — anything `threshold_from` or `applies_if` needs to read,
  e.g. `tender.turnover_requirement` (sourced from the tender's extracted
  requirements) and `bid.claims_msme_benefit`.

Each finding carries `status` (`PASS` / `FAIL` / `NEEDS_REVIEW`), a `reason`,
and both the `claimed` and `verified` values side by side — that gap between
what a vendor claims and what the government confirms is the fraud signal
the whole system exists to surface.

## Risk scoring

`backend/app/services/risk/scorer.py` turns a list of findings into a 0-100
score and a `LOW` / `MEDIUM` / `HIGH` band, weighted by each rule's `weight`.
A FAILed `BLOCKER` (e.g. the vendor is debarred) forces `HIGH` regardless of
the numeric score — one disqualifying fact should never be diluted by 26
unrelated passes.
