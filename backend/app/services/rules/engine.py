from dataclasses import dataclass, field
from typing import Any

from app.services.rules.condition import evaluate_condition
from app.services.rules.loader import Rule, RulePack
from app.services.rules.operators import evaluate as evaluate_operator

# "government" facts live in `verified`, "document" facts live in `claimed" —
# this is the vocabulary rule packs use in source_priority.
_SOURCE_TO_BUCKET = {"government": "verified", "document": "claimed"}


@dataclass
class FactValue:
    value: Any
    detail: dict = field(default_factory=dict)
    # UP means the source actually produced this value; a government fact
    # that came back DOWN/NOT_FOUND should not be passed in here at all —
    # the engine treats a missing key as "source unavailable" and falls
    # through to the next entry in source_priority.


@dataclass
class FindingResult:
    rule_id: str
    label: str
    severity: str
    weight: float
    status: str  # PASS | FAIL | NEEDS_REVIEW
    reason: str
    expected: dict
    claimed: dict | None
    verified: dict | None
    risk_contribution: float


def _fact_dict(fact: FactValue | None) -> dict | None:
    if fact is None:
        return None
    return {"value": fact.value, "source": fact.detail}


def _resolve_expected(rule: Rule, context: dict) -> tuple[Any, bool]:
    """Returns (expected_value, resolvable). resolvable is False when the rule
    depends on a threshold_from key that isn't present in context — the
    finding can't be evaluated yet, so it becomes NEEDS_REVIEW rather than a
    false PASS or FAIL."""
    if rule.threshold_from is not None:
        if rule.threshold_from not in context:
            return None, False
        return context[rule.threshold_from], True
    return rule.value, True


def _resolve_actual(rule: Rule, claimed: dict[str, FactValue], verified: dict[str, FactValue]) -> FactValue | None:
    for source in rule.source_priority:
        bucket = claimed if _SOURCE_TO_BUCKET.get(source) == "claimed" else verified
        fact = bucket.get(rule.fact)
        if fact is not None:
            return fact
    return None


def evaluate_rule_pack(
    pack: RulePack,
    *,
    claimed: dict[str, FactValue],
    verified: dict[str, FactValue],
    context: dict,
) -> list[FindingResult]:
    """Pure function: same rule pack + facts + context always produces the
    same findings. No LLM calls, no I/O — that determinism is the point."""
    results: list[FindingResult] = []

    for rule in pack.rules:
        if rule.applies_if and not evaluate_condition(rule.applies_if, context):
            continue

        claimed_fact = claimed.get(rule.fact)
        verified_fact = verified.get(rule.fact)
        expected_value, resolvable = _resolve_expected(rule, context)

        expected_out = {"operator": rule.operator, "value": expected_value}

        if not resolvable:
            results.append(
                FindingResult(
                    rule_id=rule.id,
                    label=rule.label,
                    severity=rule.severity,
                    weight=rule.weight,
                    status="NEEDS_REVIEW",
                    reason=f"Tender threshold '{rule.threshold_from}' was not extracted for this requirement.",
                    expected=expected_out,
                    claimed=_fact_dict(claimed_fact),
                    verified=_fact_dict(verified_fact),
                    risk_contribution=rule.weight * 0.5,
                )
            )
            continue

        resolved = _resolve_actual(rule, claimed, verified)
        if resolved is None:
            results.append(
                FindingResult(
                    rule_id=rule.id,
                    label=rule.label,
                    severity=rule.severity,
                    weight=rule.weight,
                    status="NEEDS_REVIEW",
                    reason=f"No value found for '{rule.fact}' from any source in {rule.source_priority}.",
                    expected=expected_out,
                    claimed=_fact_dict(claimed_fact),
                    verified=_fact_dict(verified_fact),
                    risk_contribution=rule.weight * 0.5,
                )
            )
            continue

        try:
            passed = evaluate_operator(rule.operator, resolved.value, expected_value)
            status = "PASS" if passed else "FAIL"
            reason = (
                f"{rule.label}: {resolved.value!r} {'satisfies' if passed else 'does not satisfy'} "
                f"{rule.operator} {expected_value!r}."
            )
            risk_contribution = 0.0 if passed else rule.weight
        except (TypeError, ValueError) as exc:
            status = "NEEDS_REVIEW"
            reason = f"Could not evaluate '{rule.fact}': {exc}"
            risk_contribution = rule.weight * 0.5

        results.append(
            FindingResult(
                rule_id=rule.id,
                label=rule.label,
                severity=rule.severity,
                weight=rule.weight,
                status=status,
                reason=reason,
                expected=expected_out,
                claimed=_fact_dict(claimed_fact),
                verified=_fact_dict(verified_fact),
                risk_contribution=risk_contribution,
            )
        )

    return results
