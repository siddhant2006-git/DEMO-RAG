import json

from app.services.extraction.tender_requirements import extract_requirements_from_page
from app.services.extraction.vendor_facts import extract_facts_from_page
from app.services.llm.client import OllamaClient

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
