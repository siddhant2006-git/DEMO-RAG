import re
from datetime import date, datetime

_CURRENCY_PREFIX_RE = re.compile(r"^(rs\.?|inr|₹)\s*", re.IGNORECASE)
_TRAILING_NOISE_RE = re.compile(r"(/-|\bonly\b)\s*$", re.IGNORECASE)

_NUMBER_UNIT_RE = re.compile(
    r"(?P<number>[\d,]+(?:\.\d+)?)\s*"
    r"(?P<unit>crores?|cr\.?|lakhs?|lacs?|l\.?|millions?|mn\.?|billions?|bn\.?|thousands?|k\.?)?",
    re.IGNORECASE,
)

_UNIT_MULTIPLIERS = {
    "crore": 1e7, "crores": 1e7, "cr": 1e7, "cr.": 1e7,
    "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "l": 1e5, "l.": 1e5,
    "million": 1e6, "millions": 1e6, "mn": 1e6, "mn.": 1e6,
    "billion": 1e9, "billions": 1e9, "bn": 1e9, "bn.": 1e9,
    "thousand": 1e3, "thousands": 1e3, "k": 1e3, "k.": 1e3,
}

_GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]$")
_PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")

_DATE_FORMATS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%d-%b-%Y",
)


def normalize_amount(raw: str) -> float | None:
    """Parses Indian-currency amount strings into a plain INR float.

    Handles the "Rs. 5,00,00,000" / "5 Crore" / "5cr" / "50 million" /
    "₹50,00,000" / "5,00,00,000/-" family — a normalizer at this one boundary
    so the rule engine never compares raw strings.
    """
    if not raw:
        return None

    text = raw.strip()
    text = _CURRENCY_PREFIX_RE.sub("", text)
    text = _TRAILING_NOISE_RE.sub("", text).strip()

    match = _NUMBER_UNIT_RE.search(text)
    if not match:
        return None

    number_str = match.group("number").replace(",", "")
    try:
        number = float(number_str)
    except ValueError:
        return None

    unit = (match.group("unit") or "").lower().strip()
    multiplier = _UNIT_MULTIPLIERS.get(unit, 1.0)
    return number * multiplier


def normalize_gstin(raw: str) -> str | None:
    if not raw:
        return None
    candidate = re.sub(r"\s+", "", raw).upper()
    return candidate if _GSTIN_RE.match(candidate) else None


def normalize_pan(raw: str) -> str | None:
    if not raw:
        return None
    candidate = re.sub(r"\s+", "", raw).upper()
    return candidate if _PAN_RE.match(candidate) else None


def normalize_date(raw: str) -> date | None:
    if not raw:
        return None
    text = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def normalize_years(raw: str) -> float | None:
    if not raw:
        return None
    match = re.search(r"\d+(?:\.\d+)?", raw)
    return float(match.group()) if match else None
