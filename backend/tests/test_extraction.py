from datetime import date

import pytest

from app.services.extraction.normalizers import (
    normalize_amount,
    normalize_date,
    normalize_gstin,
    normalize_pan,
    normalize_years,
)

AMOUNT_CASES = [
    ("Rs. 5,00,00,000", 50_000_000),
    ("5 Crore", 50_000_000),
    ("5cr", 50_000_000),
    ("5 Cr.", 50_000_000),
    ("50 million", 50_000_000),
    ("₹50,00,000", 5_000_000),
    ("INR 5 Cr", 50_000_000),
    ("Rs 5.5 Crores", 55_000_000),
    ("5 lakh", 500_000),
    ("5L", 500_000),
    ("50 Lakhs", 5_000_000),
    ("5,00,00,000/-", 50_000_000),
    ("500000", 500_000),
    ("Rs.1,00,000/-", 100_000),
    ("2.5 Cr", 25_000_000),
    ("10000000", 10_000_000),
    ("1 Lac", 100_000),
    ("3.2 million", 3_200_000),
    ("Rs. 25 Lakhs only", 2_500_000),
    ("₹1.2 Billion", 1_200_000_000),
    ("2 bn", 2_000_000_000),
    ("Rs 500 Thousand", 500_000),
    ("10k", 10_000),
    ("  Rs.  50,00,000  ", 5_000_000),
    ("rs. 5 crore", 50_000_000),
    ("INR5Cr", 50_000_000),
    ("Rs.2,50,00,000/-", 25_000_000),
    ("1,000,000", 1_000_000),
    ("0.5 Cr", 5_000_000),
    ("₹ 5,00,000/- only", 500_000),
]


@pytest.mark.parametrize("raw,expected", AMOUNT_CASES)
def test_normalize_amount(raw, expected):
    assert normalize_amount(raw) == pytest.approx(expected)


def test_normalize_amount_unparseable_returns_none():
    assert normalize_amount("not an amount") is None
    assert normalize_amount("") is None
    assert normalize_amount(None) is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("27AAAPL1234C1Z5", "27AAAPL1234C1Z5"),
        ("27aaapl1234c1z5", "27AAAPL1234C1Z5"),
        (" 27AAAPL1234C1Z5 ", "27AAAPL1234C1Z5"),
        ("not-a-gstin", None),
        ("27AAAPL1234C1Z", None),  # too short
        ("", None),
    ],
)
def test_normalize_gstin(raw, expected):
    assert normalize_gstin(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("AAAPL1234C", "AAAPL1234C"),
        ("aaapl1234c", "AAAPL1234C"),
        ("AAAPL1234", None),
        ("", None),
    ],
)
def test_normalize_pan(raw, expected):
    assert normalize_pan(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("01/04/2018", date(2018, 4, 1)),
        ("01-04-2018", date(2018, 4, 1)),
        ("2018-04-01", date(2018, 4, 1)),
        ("01.04.2018", date(2018, 4, 1)),
        ("1 April 2018", date(2018, 4, 1)),
        ("1 Apr 2018", date(2018, 4, 1)),
        ("April 1, 2018", date(2018, 4, 1)),
        ("garbage date", None),
    ],
)
def test_normalize_date(raw, expected):
    assert normalize_date(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("5 years", 5.0),
        ("5+ years", 5.0),
        ("at least 5 years", 5.0),
        ("5.5 years", 5.5),
        ("no experience", None),
    ],
)
def test_normalize_years(raw, expected):
    assert normalize_years(raw) == expected
