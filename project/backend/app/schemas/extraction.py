from typing import Literal

from pydantic import BaseModel

REQUIREMENT_CATEGORIES = Literal[
    "turnover", "experience", "certification", "registration",
    "financial", "technical", "msme", "debarment", "manual_review",
]

OPERATORS = Literal["gte", "lte", "gt", "lt", "eq", "in", "regex", "date_before", "date_after", "exists"]


class ExtractedRequirement(BaseModel):
    text: str
    category: REQUIREMENT_CATEGORIES
    expected_operator: OPERATORS | None = None
    expected_value: str | float | bool | None = None
    expected_unit: str | None = None
    # verbatim quote from the tender page that justifies this requirement —
    # checked against the source text before it's trusted (see snippet_guard)
    source_snippet: str


class RequirementExtractionResult(BaseModel):
    requirements: list[ExtractedRequirement]


class ExtractedFact(BaseModel):
    # dotted path matching the rule pack vocabulary, e.g. financials.avg_annual_turnover
    fact_key: str
    raw_value: str
    source_snippet: str


class VendorFactExtractionResult(BaseModel):
    facts: list[ExtractedFact]
