from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.requirement import Requirement
from app.models.tender import Tender
from app.services.rules.loader import Rule

_CATEGORY_KEYWORDS = (
    ("TURNOVER", "turnover"),
    ("EXPERIENCE", "experience"),
    ("SIMILAR-WORK", "experience"),
    ("GST", "registration"),
    ("PAN", "registration"),
    ("MSME", "msme"),
    ("DEBARMENT", "debarment"),
    ("CERTIFICATION", "certification"),
    ("EMD", "financial"),
)


def _infer_category(rule: Rule) -> str:
    for keyword, category in _CATEGORY_KEYWORDS:
        if keyword in rule.id.upper():
            return category
    return "manual_review"


def get_or_create_requirement_for_rule(db: Session, tender: Tender, rule: Rule) -> Requirement:
    """Links a rule to a Requirement row an officer can see and edit.

    Convention: when Phase 2's LLM extraction runs, it should set
    Requirement.external_ref to the matching rule id (e.g. "REQ-TURNOVER") so
    this finds the real, page-sourced requirement instead of falling back to
    one synthesized from the rule pack itself.
    """
    existing = db.execute(
        select(Requirement).where(Requirement.tender_id == tender.id, Requirement.external_ref == rule.id)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    requirement = Requirement(
        tender_id=tender.id,
        external_ref=rule.id,
        text=rule.label,
        category=_infer_category(rule),
        expected={"operator": rule.operator, "value": rule.value},
        human_reviewed=False,
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement
