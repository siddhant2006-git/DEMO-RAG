import pytest

from app.services.extraction.fact_normalization import normalize_fact


@pytest.mark.parametrize(
    "fact_key,raw_value,expected_value",
    [
        ("financials.avg_annual_turnover", "Rs. 6,20,00,000", 62_000_000),
        ("experience.similar_work_value", "5 Cr", 50_000_000),
        ("financials.emd_submitted", "Yes", True),
        ("financials.emd_submitted", "No", False),
        ("udyam.valid", "Active", True),
        ("debarment.listed", "false", False),
        ("bid.claims_msme_benefit", "true", True),
        ("experience.years", "8 years", 8.0),
        ("identity.gstin", "27AAAPL1234C1Z5", "27AAAPL1234C1Z5"),
        ("identity.pan", "aaapl1234c", "AAAPL1234C"),
        ("gst.status", "ACTIVE", "ACTIVE"),
        ("udyam.category", "Small", "Small"),
    ],
)
def test_normalize_fact(fact_key, raw_value, expected_value):
    result = normalize_fact(fact_key, raw_value)
    assert result["value"] == expected_value


def test_unparseable_amount_yields_none_not_a_crash():
    result = normalize_fact("financials.avg_annual_turnover", "a lot of money")
    assert result["value"] is None


def test_ambiguous_bool_yields_none():
    result = normalize_fact("udyam.valid", "maybe")
    assert result["value"] is None
