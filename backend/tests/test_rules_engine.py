import pytest

from app.core.errors import AppError
from app.services.rules.engine import FactValue, evaluate_rule_pack
from app.services.rules.loader import load_rule_pack
from app.services.risk.scorer import score_findings

RULES_DIR = "rules"


@pytest.fixture
def goods_pack():
    return load_rule_pack(f"{RULES_DIR}/default_goods.yaml")


def test_government_value_beats_claimed_value(goods_pack):
    """The core fraud-detection behavior: bid claims 6.2 Cr, GST shows 4.1 Cr,
    tender requires 5 Cr — the government figure must win and the finding
    must FAIL."""
    claimed = {"financials.avg_annual_turnover": FactValue(62_000_000)}
    verified = {"financials.avg_annual_turnover": FactValue(41_000_000)}
    context = {"tender.turnover_requirement": 50_000_000, "bid.claims_msme_benefit": False}

    results = evaluate_rule_pack(goods_pack, claimed=claimed, verified=verified, context=context)
    turnover_finding = next(r for r in results if r.rule_id == "REQ-TURNOVER")

    assert turnover_finding.status == "FAIL"
    assert turnover_finding.claimed["value"] == 62_000_000
    assert turnover_finding.verified["value"] == 41_000_000


def test_applies_if_skips_inapplicable_rule(goods_pack):
    claimed, verified = {}, {}
    context = {"tender.turnover_requirement": 1, "bid.claims_msme_benefit": False}
    results = evaluate_rule_pack(goods_pack, claimed=claimed, verified=verified, context=context)
    assert all(r.rule_id != "REQ-MSME" for r in results)


def test_applies_if_includes_rule_when_true(goods_pack):
    claimed, verified = {}, {}
    context = {"tender.turnover_requirement": 1, "bid.claims_msme_benefit": True}
    results = evaluate_rule_pack(goods_pack, claimed=claimed, verified=verified, context=context)
    msme = next(r for r in results if r.rule_id == "REQ-MSME")
    assert msme.status == "NEEDS_REVIEW"  # no udyam.valid fact supplied


def test_missing_threshold_is_needs_review_not_a_crash(goods_pack):
    results = evaluate_rule_pack(
        goods_pack, claimed={}, verified={}, context={"bid.claims_msme_benefit": False}
    )
    turnover = next(r for r in results if r.rule_id == "REQ-TURNOVER")
    assert turnover.status == "NEEDS_REVIEW"


def test_deterministic_across_runs(goods_pack):
    claimed = {"financials.avg_annual_turnover": FactValue(62_000_000)}
    verified = {"financials.avg_annual_turnover": FactValue(41_000_000), "gst.status": FactValue("ACTIVE")}
    context = {"tender.turnover_requirement": 50_000_000, "bid.claims_msme_benefit": False}

    runs = [
        [(r.rule_id, r.status, r.risk_contribution) for r in evaluate_rule_pack(
            goods_pack, claimed=claimed, verified=verified, context=context
        )]
        for _ in range(10)
    ]
    assert all(run == runs[0] for run in runs)


def test_blocker_fail_forces_high_risk_band(goods_pack):
    claimed = {"financials.avg_annual_turnover": FactValue(100_000_000), "identity.pan": FactValue("AAAPL1234C")}
    verified = {
        "financials.avg_annual_turnover": FactValue(100_000_000),
        "gst.status": FactValue("ACTIVE"),
        "debarment.listed": FactValue(True),  # BLOCKER fail
    }
    context = {"tender.turnover_requirement": 1, "bid.claims_msme_benefit": False}

    results = evaluate_rule_pack(goods_pack, claimed=claimed, verified=verified, context=context)
    assessment = score_findings(results)

    assert assessment.band == "HIGH"
    assert assessment.forced_by_blocker is True


def test_all_pass_is_low_risk(goods_pack):
    claimed = {"financials.avg_annual_turnover": FactValue(100_000_000), "identity.pan": FactValue("AAAPL1234C")}
    verified = {
        "financials.avg_annual_turnover": FactValue(100_000_000),
        "gst.status": FactValue("ACTIVE"),
        "debarment.listed": FactValue(False),
    }
    context = {
        "tender.turnover_requirement": 1,
        "tender.experience_requirement": 1,
        "bid.claims_msme_benefit": False,
    }
    claimed["experience.years"] = FactValue(10)

    results = evaluate_rule_pack(goods_pack, claimed=claimed, verified=verified, context=context)
    assessment = score_findings(results)

    assert assessment.band == "LOW"
    assert assessment.fail_count == 0


def test_malformed_rule_pack_reports_line_number(tmp_path):
    bad_pack = tmp_path / "bad.yaml"
    bad_pack.write_text(
        "version: 1\nname: Bad\nrules:\n  - id: REQ-X\n    label: X\n    severity: NOPE\n"
        "    weight: 1\n    fact: a\n    operator: eq\n    value: 1\n",
        encoding="utf-8",
    )
    with pytest.raises(AppError) as exc_info:
        load_rule_pack(bad_pack)
    assert "line" in exc_info.value.message
