/* Node side of explainer/parity_check.py.

   Reads a JSON job on stdin, runs it through the browser engine port, and
   writes the results to stdout as JSON. Nothing here should contain judgement
   logic of its own — it exists only to let the same scenarios run through
   assets/engine.js that parity_check.py runs through the real Python.

       node parity_runner.js < job.json > out.json
*/
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const here = __dirname;
const sandbox = { window: {}, console: console };
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

for (const f of ['data.js', 'engine.js']) {
  const src = fs.readFileSync(path.join(here, 'assets', f), 'utf8');
  vm.runInContext(src, sandbox, { filename: f });
}

const E = sandbox.window.TGEngine;
const D = sandbox.window.TGData;

const job = JSON.parse(fs.readFileSync(0, 'utf8'));

function toFacts(raw) {
  const out = {};
  for (const [k, v] of Object.entries(raw)) {
    out[k] = E.FactValue(v.value, v.detail || {}, v.conflicts || []);
  }
  return out;
}

const results = job.scenarios.map((s) => {
  const pack = { name: s.pack.name, version: s.pack.version, rules: s.pack.rules };
  const findings = E.evaluateRulePack(pack, toFacts(s.claimed), toFacts(s.verified), s.context);
  const risk = E.scoreFindings(findings);
  return {
    name: s.name,
    findings: findings.map((f) => ({
      rule_id: f.rule_id,
      status: f.status,
      risk_contribution: f.risk_contribution,
      expected_value: f.expected.value === undefined ? null : f.expected.value
    })),
    risk: { score: risk.score, band: risk.band, forced_by_blocker: risk.forced_by_blocker }
  };
});

// Also hand back the transcribed rule packs so the Python side can diff them
// against the real YAML in backend/rules/.
const packs = {};
for (const [key, p] of Object.entries(D.RULE_PACKS)) {
  packs[key] = {
    version: p.version,
    name: p.name,
    rules: p.rules.map((r) => ({
      id: r.id, label: r.label, severity: r.severity, weight: r.weight,
      fact: r.fact, operator: r.operator,
      value: r.value === undefined ? null : r.value,
      threshold_from: r.threshold_from === undefined ? null : r.threshold_from,
      source_priority: r.source_priority || ['document'],
      applies_if: r.applies_if === undefined ? null : r.applies_if
    }))
  };
}

const normalizerCases = job.normalizer_cases.map((raw) => ({
  raw: raw,
  amount: E.normalizeAmount(raw)
}));

const snippetCases = job.snippet_cases.map((c) => ({
  snippet: c,
  grounded: E.isSnippetGrounded(c, D.PAGE_TEXT)
}));

process.stdout.write(JSON.stringify({
  results: results,
  packs: packs,
  normalizer_cases: normalizerCases,
  snippet_cases: snippetCases,
  page_text: D.PAGE_TEXT
}, null, 2));
