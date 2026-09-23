from dataclasses import dataclass

from app.services.rules.engine import FindingResult

LOW_MAX = 33
MEDIUM_MAX = 65
HIGH_FLOOR_FOR_BLOCKER = 66


@dataclass
class RiskAssessment:
    score: float  # 0-100, higher = riskier
    band: str  # LOW | MEDIUM | HIGH
    forced_by_blocker: bool
    pass_count: int
    fail_count: int
    needs_review_count: int


def _band_for(score: float) -> str:
    if score > MEDIUM_MAX:
        return "HIGH"
    if score > LOW_MAX:
        return "MEDIUM"
    return "LOW"


def score_findings(findings: list[FindingResult]) -> RiskAssessment:
    """Weighted 0-100 risk score. A FAILed BLOCKER-severity requirement (e.g.
    the vendor is debarred) forces the HIGH band regardless of how well
    everything else scored — a single disqualifying fact should never be
    diluted by 26 unrelated passes."""
    total_weight = sum(f.weight for f in findings)
    total_risk = sum(f.risk_contribution for f in findings)
    raw_score = (total_risk / total_weight * 100) if total_weight else 0.0

    blocker_failed = any(f.severity == "BLOCKER" and f.status == "FAIL" for f in findings)
    score = max(raw_score, HIGH_FLOOR_FOR_BLOCKER) if blocker_failed else raw_score
    band = "HIGH" if blocker_failed else _band_for(score)

    return RiskAssessment(
        score=round(score, 1),
        band=band,
        forced_by_blocker=blocker_failed,
        pass_count=sum(1 for f in findings if f.status == "PASS"),
        fail_count=sum(1 for f in findings if f.status == "FAIL"),
        needs_review_count=sum(1 for f in findings if f.status == "NEEDS_REVIEW"),
    )
