import json

from app.services.compliance.requirement_binding import match_rule_for_extracted
from app.services.extraction.tender_requirements import extract_requirements_from_page
from app.services.extraction.vendor_facts import extract_facts_from_page
from app.services.llm.client import OllamaClient
from app.services.rules.loader import load_rule_pack

PAGE_TEXT = "3. Eligibility Criteria\nBidder must have average annual turnover >= 5 Cr in last 3 FY."
BID_TEXT = "Financial details: Average annual turnover for the last 3 financial years is Rs. 6,20,00,000."


def test_short_page_skips_llm_call(monkeypatch):
    called = []
    monkeypatch.setattr(OllamaClient, "generate", lambda self, *a, **k: called.append(1) or "{}")
    result = extract_requirements_from_page(OllamaClient.__new__(OllamaClient), page_number=1, page_text="short")
    assert result == []
    assert called == []


def test_grounded_requirement_is_kept(monkeypatch):
    response = json.dumps(
        {
            "requirements": [
                {
                    "text": "Minimum turnover requirement",
                    "category": "turnover",
                    "expected_operator": "gte",
                    "expected_value": 50000000,
                    "expected_unit": "INR",
                    "source_snippet": "Bidder must have average annual turnover >= 5 Cr in last 3 FY.",
                }
            ]
        }
    )
    monkeypatch.setattr(OllamaClient, "generate", lambda self, *a, **k: response)
    result = extract_requirements_from_page(OllamaClient.__new__(OllamaClient), page_number=3, page_text=PAGE_TEXT)
    assert len(result) == 1
    assert result[0].category == "turnover"


def test_hallucinated_requirement_is_dropped(monkeypatch):
    response = json.dumps(
        {
            "requirements": [
                {
                    "text": "ISO certification required",
                    "category": "certification",
                    "source_snippet": "Bidder must hold ISO 9001 certification.",  # not in PAGE_TEXT
                }
            ]
        }
    )
    monkeypatch.setattr(OllamaClient, "generate", lambda self, *a, **k: response)
    result = extract_requirements_from_page(OllamaClient.__new__(OllamaClient), page_number=3, page_text=PAGE_TEXT)
    assert result == []


def test_grounded_fact_is_normalized(monkeypatch):
    response = json.dumps(
        {
            "facts": [
                {
                    "fact_key": "financials.avg_annual_turnover",
                    "raw_value": "Rs. 6,20,00,000",
                    "source_snippet": "Average annual turnover for the last 3 financial years is Rs. 6,20,00,000.",
                }
            ]
        }
    )
    monkeypatch.setattr(OllamaClient, "generate", lambda self, *a, **k: response)
    result = extract_facts_from_page(OllamaClient.__new__(OllamaClient), page_number=12, page_text=BID_TEXT)
    assert len(result) == 1
    assert result[0].normalized_value["value"] == 62_000_000
    assert result[0].page_number == 12


def test_match_rule_for_extracted_disambiguates_same_category_by_keyword():
    """The goods pack maps both REQ-GST-ACTIVE and REQ-PAN to the
    'registration' category (see requirement_binding._CATEGORY_KEYWORDS) —
    an extracted requirement whose text names PAN must bind to REQ-PAN, not
    whichever registration rule happens to be first."""
    pack = load_rule_pack("rules/default_goods.yaml")

    rule = match_rule_for_extracted(
        pack, category="registration", text="Valid PAN card required for the bidder", used_refs=set()
    )
    assert rule.id == "REQ-PAN"

    rule = match_rule_for_extracted(
        pack, category="registration", text="Active GST registration required", used_refs=set()
    )
    assert rule.id == "REQ-GST-ACTIVE"


def test_match_rule_for_extracted_skips_already_used_refs():
    pack = load_rule_pack("rules/default_goods.yaml")
    rule = match_rule_for_extracted(
        pack, category="turnover", text="Minimum turnover requirement", used_refs={"REQ-TURNOVER"}
    )
    assert rule is None


def test_match_rule_for_extracted_returns_none_for_uncovered_category():
    pack = load_rule_pack("rules/default_goods.yaml")
    rule = match_rule_for_extracted(pack, category="manual_review", text="Some novel clause", used_refs=set())
    assert rule is None
