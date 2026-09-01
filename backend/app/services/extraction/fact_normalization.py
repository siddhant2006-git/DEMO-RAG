from app.services.extraction.normalizers import (
    normalize_amount,
    normalize_gstin,
    normalize_pan,
    normalize_years,
)

_TRUE_WORDS = {"yes", "true", "y", "active", "valid", "submitted", "certified", "claimed", "1"}
_FALSE_WORDS = {"no", "false", "n", "inactive", "invalid", "not submitted", "not certified", "0"}

_AMOUNT_KEYS = {"financials.avg_annual_turnover", "experience.similar_work_value"}
_BOOL_KEYS = {
    "financials.emd_submitted",
    "udyam.valid",
    "certification.iso_certified",
    "debarment.listed",
    "bid.claims_msme_benefit",
}
_YEARS_KEYS = {"experience.years"}
_GSTIN_KEYS = {"identity.gstin"}
_PAN_KEYS = {"identity.pan"}


def _normalize_bool(raw: str) -> bool | None:
    lowered = raw.strip().lower()
    if lowered in _TRUE_WORDS:
        return True
    if lowered in _FALSE_WORDS:
        return False
    return None


def normalize_fact(fact_key: str, raw_value: str) -> dict:
    """Maps a raw extracted string to a typed value per the rule pack's fact
    vocabulary, so the rule engine (app.services.rules) never has to parse
    strings itself — that boundary is exactly what the "chaotic formats" hard
    problem calls for.

    Returns {"value": <typed or None>, "unit": <str|None>}. value is None
    when the raw string couldn't be parsed — callers should treat that as
    "extraction found something but it's unusable" rather than silently
    dropping it.
    """
    if fact_key in _AMOUNT_KEYS:
        return {"value": normalize_amount(raw_value), "unit": "INR"}
    if fact_key in _BOOL_KEYS:
        return {"value": _normalize_bool(raw_value), "unit": None}
    if fact_key in _YEARS_KEYS:
        return {"value": normalize_years(raw_value), "unit": "years"}
    if fact_key in _GSTIN_KEYS:
        return {"value": normalize_gstin(raw_value), "unit": None}
    if fact_key in _PAN_KEYS:
        return {"value": normalize_pan(raw_value), "unit": None}
    # gst.status, udyam.category and anything unrecognized pass through as-is
    return {"value": raw_value.strip(), "unit": None}
