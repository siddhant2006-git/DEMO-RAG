#!/usr/bin/env python
"""Proves explainer/assets/engine.js still agrees with the real Python.

The explainer tells the reader that its live bench runs a faithful port of the
decision layer. This checks that claim four ways:

  1. Rule packs      — data.js RULE_PACKS vs backend/rules/*.yaml
  2. Rule engine     — evaluateRulePack() vs evaluate_rule_pack(), per scenario
  3. Risk scorer     — scoreFindings()    vs score_findings()
  4. Normalizers     — normalizeAmount() / isSnippetGrounded() vs their originals

Run it after touching either side:

    backend/.venv/Scripts/python.exe explainer/parity_check.py

Needs `node` on PATH. Exits non-zero on any mismatch.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.extraction.normalizers import normalize_amount  # noqa: E402
from app.services.extraction.snippet_guard import is_snippet_grounded  # noqa: E402
from app.services.risk.scorer import score_findings  # noqa: E402
from app.services.rules.engine import FactValue, evaluate_rule_pack  # noqa: E402
from app.services.rules.loader import load_rule_pack  # noqa: E402

RULES_DIR = PROJECT_ROOT / "backend" / "rules"

# --------------------------------------------------------------------------
# Scenarios — each one exercises a different branch of engine.py.
# --------------------------------------------------------------------------

GANGA_CLAIMED = {
    "financials.avg_annual_turnover": {"value": 62000000.0, "detail": {"page": 2, "snippet": "Rs. 6,20,00,000"}},
    "experience.years": {"value": 8.0, "detail": {"page": 2, "snippet": "8 years"}},
    "identity.pan": {"value": "AAAPL1234C", "detail": {"page": 2, "snippet": "AAAPL1234C"}},
}
GANGA_VERIFIED = {
    "gst.status": {"value": "ACTIVE", "detail": {"portal": "GST"}},
    "gst.legal_name": {"value": "Ganga Infra Projects Pvt Ltd", "detail": {"portal": "GST"}},
    "financials.avg_annual_turnover": {"value": 41000000, "detail": {"portal": "GST"}},
    "debarment.listed": {"value": False, "detail": {"portal": "DEBARMENT"}},
    "udyam.valid": {"value": True, "detail": {"portal": "UDYAM"}},
}
FULL_CONTEXT = {
    "bid.claims_msme_benefit": False,
    "tender.turnover_requirement": 50000000.0,
    "tender.experience_requirement": 5.0,
}

SCENARIOS = [
    {
        "name": "demo bid — government value beats the claim",
        "pack": "goods", "claimed": GANGA_CLAIMED, "verified": GANGA_VERIFIED, "context": FULL_CONTEXT,
    },
    {
        "name": "msme claimed — applies_if brings the rule in",
        "pack": "goods", "claimed": GANGA_CLAIMED, "verified": GANGA_VERIFIED,
        "context": dict(FULL_CONTEXT, **{"bid.claims_msme_benefit": True}),
    },
    {
        "name": "no tender threshold — unresolvable expected value",
        "pack": "goods", "claimed": GANGA_CLAIMED, "verified": GANGA_VERIFIED,
        "context": {"bid.claims_msme_benefit": False},
    },
    {
        "name": "GST portal down — no verified facts at all",
        "pack": "goods", "claimed": GANGA_CLAIMED,
        "verified": {"debarment.listed": {"value": False, "detail": {"portal": "DEBARMENT"}}},
        "context": FULL_CONTEXT,
    },
    {
        "name": "debarred vendor — blocker override",
        "pack": "goods", "claimed": GANGA_CLAIMED,
        "verified": dict(GANGA_VERIFIED, **{"debarment.listed": {"value": True, "detail": {"portal": "DEBARMENT"}}}),
        "context": FULL_CONTEXT,
    },
    {
        "name": "cancelled GST registration",
        "pack": "goods", "claimed": GANGA_CLAIMED,
        "verified": dict(GANGA_VERIFIED, **{"gst.status": {"value": "CANCELLED", "detail": {"portal": "GST"}}}),
        "context": FULL_CONTEXT,
    },
    {
        "name": "bid contradicts itself across pages",
        "pack": "goods",
        "claimed": dict(GANGA_CLAIMED, **{
            "financials.avg_annual_turnover": {
                "value": 62000000.0, "detail": {"page": 2, "snippet": "Rs. 6,20,00,000"},
                "conflicts": [
                    {"value": 62000000.0, "page": 2, "snippet": "Rs. 6,20,00,000"},
                    {"value": 31000000.0, "page": 5, "snippet": "Rs. 3,10,00,000"},
                ],
            }
        }),
        "verified": GANGA_VERIFIED, "context": FULL_CONTEXT,
    },
    {
        "name": "no facts whatsoever",
        "pack": "goods", "claimed": {}, "verified": {}, "context": FULL_CONTEXT,
    },
    {
        "name": "works pack — emd blocker and similar-work value",
        "pack": "works",
        "claimed": dict(GANGA_CLAIMED, **{
            "experience.similar_work_value": {"value": 30000000.0, "detail": {"page": 3, "snippet": "3 Cr"}},
            "financials.emd_submitted": {"value": True, "detail": {"page": 1, "snippet": "EMD enclosed"}},
        }),
        "verified": GANGA_VERIFIED,
        "context": dict(FULL_CONTEXT, **{"tender.similar_work_value_requirement": 40000000.0}),
    },
    {
        "name": "services pack — iso certification missing",
        "pack": "services",
        "claimed": dict(GANGA_CLAIMED, **{
            "certification.iso_certified": {"value": False, "detail": {"page": 4, "snippet": "not certified"}},
        }),
        "verified": GANGA_VERIFIED, "context": FULL_CONTEXT,
    },
    {
        "name": "malformed pan was dropped by the normalizer",
        "pack": "goods",
        "claimed": {k: v for k, v in GANGA_CLAIMED.items() if k != "identity.pan"},
        "verified": GANGA_VERIFIED, "context": FULL_CONTEXT,
    },
]

NORMALIZER_CASES = [
    "Rs. 6,20,00,000", "6.2 Crore", "5cr", "₹50,00,000", "62 lakh", "50 million",
    "5,00,00,000/-", "about five crore", "2.5 bn", "300 thousand", "", "no digits here",
    "INR 1,00,000 only", "7 Lacs", "12", "9.75 Cr.",
]

SNIPPET_CASES = [
    "an average annual turnover of at least Rs. 5 Crore",
    "must hold a valid and active GST registration",
    "minimum average annual turnover of Rs. 5 crore",
    "a minimum of 3 years of relevant experience",
    "The bidder must hold ISO 9001:2015 certification.",
    "THE  BIDDER   MUST NOT BE currently debarred",
    "",
    "   ",
    "3.5 The bidder's PAN must be provided and correctly formatted.",
]

# --------------------------------------------------------------------------


def as_facts(raw: dict) -> dict:
    return {
        key: FactValue(value=spec["value"], detail=spec.get("detail", {}), conflicts=spec.get("conflicts", []))
        for key, spec in raw.items()
    }


def rule_to_dict(rule) -> dict:
    return {
        "id": rule.id, "label": rule.label, "severity": rule.severity, "weight": rule.weight,
        "fact": rule.fact, "operator": rule.operator, "value": rule.value,
        "threshold_from": rule.threshold_from, "source_priority": list(rule.source_priority),
        "applies_if": rule.applies_if,
    }


def run_python(packs: dict) -> list[dict]:
    out = []
    for scenario in SCENARIOS:
        pack = packs[scenario["pack"]]
        findings = evaluate_rule_pack(
            pack,
            claimed=as_facts(scenario["claimed"]),
            verified=as_facts(scenario["verified"]),
            context=scenario["context"],
        )
        risk = score_findings(findings)
        out.append({
            "name": scenario["name"],
            "findings": [
                {
                    "rule_id": f.rule_id, "status": f.status,
                    "risk_contribution": f.risk_contribution,
                    "expected_value": f.expected["value"],
                }
                for f in findings
            ],
            "risk": {"score": risk.score, "band": risk.band, "forced_by_blocker": risk.forced_by_blocker},
        })
    return out


def main() -> int:
    packs = {key: load_rule_pack(RULES_DIR / f"default_{key}.yaml") for key in ("goods", "works", "services")}

    job = {
        "scenarios": [
            {
                "name": s["name"],
                "pack": {"name": packs[s["pack"]].name, "version": packs[s["pack"]].version,
                         "rules": [rule_to_dict(r) for r in packs[s["pack"]].rules]},
                "claimed": s["claimed"], "verified": s["verified"], "context": s["context"],
            }
            for s in SCENARIOS
        ],
        "normalizer_cases": NORMALIZER_CASES,
        "snippet_cases": SNIPPET_CASES,
    }

    try:
        proc = subprocess.run(
            ["node", str(HERE / "parity_runner.js")],
            input=json.dumps(job), capture_output=True, text=True, encoding="utf-8", check=True,
        )
    except FileNotFoundError:
        print("node is not on PATH — install Node or run this where node is available.")
        return 2
    except subprocess.CalledProcessError as exc:
        print("parity_runner.js failed:\n" + (exc.stderr or ""))
        return 2

    js = json.loads(proc.stdout)
    failures: list[str] = []

    # 1 — rule pack transcription -------------------------------------------
    for key, pack in packs.items():
        want = {"version": pack.version, "name": pack.name, "rules": [rule_to_dict(r) for r in pack.rules]}
        got = js["packs"].get(key)
        if got != want:
            failures.append(f"rule pack '{key}': data.js does not match backend/rules/default_{key}.yaml")
            for i, (a, b) in enumerate(zip(want["rules"], got["rules"] if got else [])):
                for field in a:
                    if a[field] != b.get(field):
                        failures.append(f"    rules[{i}].{field}: yaml={a[field]!r} data.js={b.get(field)!r}")
            if got and len(got["rules"]) != len(want["rules"]):
                failures.append(f"    rule count: yaml={len(want['rules'])} data.js={len(got['rules'])}")

    # 2 + 3 — engine and scorer --------------------------------------------
    for py, node in zip(run_python(packs), js["results"]):
        if py != node:
            failures.append(f"scenario '{py['name']}':")
            if py["risk"] != node["risk"]:
                failures.append(f"    risk: python={py['risk']} js={node['risk']}")
            by_id = {f["rule_id"]: f for f in node["findings"]}
            for f in py["findings"]:
                g = by_id.get(f["rule_id"])
                if g != f:
                    failures.append(f"    {f['rule_id']}: python={f} js={g}")
            extra = set(by_id) - {f["rule_id"] for f in py["findings"]}
            for rid in sorted(extra):
                failures.append(f"    {rid}: produced by js only")

    # 4 — normalizers -------------------------------------------------------
    for case in js["normalizer_cases"]:
        want = normalize_amount(case["raw"])
        got = case["amount"]
        same = (want is None and got is None) or (
            want is not None and got is not None and abs(want - got) < 1e-6
        )
        if not same:
            failures.append(f"normalize_amount({case['raw']!r}): python={want!r} js={got!r}")

    page_text = js["page_text"]
    for case in js["snippet_cases"]:
        want = is_snippet_grounded(case["snippet"], page_text)
        if want != case["grounded"]:
            failures.append(f"is_snippet_grounded({case['snippet']!r}): python={want} js={case['grounded']}")

    total = (
        len(packs)
        + len(SCENARIOS)
        + len(NORMALIZER_CASES)
        + len(SNIPPET_CASES)
    )
    if failures:
        print("PARITY MISMATCH\n")
        for line in failures:
            print("  " + line)
        print(f"\n{len(failures)} problem(s) across {total} checks.")
        return 1

    print(f"engine.js matches the Python across {total} checks:")
    print(f"  {len(packs)} rule packs transcribed from backend/rules/*.yaml")
    print(f"  {len(SCENARIOS)} engine + scorer scenarios")
    print(f"  {len(NORMALIZER_CASES)} normalize_amount cases")
    print(f"  {len(SNIPPET_CASES)} snippet-guard cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
