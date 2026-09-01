from app.services.extraction.snippet_guard import is_snippet_grounded

SOURCE = """
3. Eligibility Criteria

Bidder must have average annual turnover >= 5 Cr in last 3 FY.
Bidder must hold a valid GST registration.
"""


def test_exact_match_is_grounded():
    assert is_snippet_grounded("Bidder must hold a valid GST registration.", SOURCE)


def test_whitespace_differences_are_ignored():
    snippet = "Bidder   must hold\na valid GST registration."
    assert is_snippet_grounded(snippet, SOURCE)


def test_case_insensitive():
    assert is_snippet_grounded("bidder must hold a valid gst registration.", SOURCE)


def test_hallucinated_snippet_is_rejected():
    assert not is_snippet_grounded("Bidder must have ISO 9001 certification.", SOURCE)


def test_empty_snippet_is_rejected():
    assert not is_snippet_grounded("", SOURCE)
    assert not is_snippet_grounded("   ", SOURCE)


def test_partial_fabrication_is_rejected():
    # real prefix, fabricated suffix — must not pass on partial overlap
    assert not is_snippet_grounded("Bidder must have average annual turnover >= 50 Cr", SOURCE)
