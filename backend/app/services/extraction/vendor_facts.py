from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_logger
from app.schemas.extraction import ExtractedFact, VendorFactExtractionResult
from app.services.extraction.fact_normalization import normalize_fact
from app.services.extraction.snippet_guard import is_snippet_grounded
from app.services.llm.client import OllamaClient
from app.services.llm.json_guard import extract_structured

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parents[1] / "llm" / "prompts" / "vendor_fact_extraction.txt"
_MIN_PAGE_CHARS = 20


@dataclass
class GroundedFact:
    page_number: int
    fact_key: str
    raw_value: str
    normalized_value: dict  # {"value": ..., "unit": ...}
    source_snippet: str


def extract_facts_from_page(client: OllamaClient, *, page_number: int, page_text: str) -> list[GroundedFact]:
    if len(page_text.strip()) < _MIN_PAGE_CHARS:
        return []

    prompt = _PROMPT_PATH.read_text(encoding="utf-8").format(page_number=page_number, page_text=page_text)
    result: VendorFactExtractionResult = extract_structured(client, prompt, VendorFactExtractionResult)

    grounded: list[GroundedFact] = []
    for fact in result.facts:
        if not is_snippet_grounded(fact.source_snippet, page_text):
            logger.warning(
                "fact_snippet_not_grounded_dropping", page_number=page_number, fact_key=fact.fact_key
            )
            continue
        grounded.append(
            GroundedFact(
                page_number=page_number,
                fact_key=fact.fact_key,
                raw_value=fact.raw_value,
                normalized_value=normalize_fact(fact.fact_key, fact.raw_value),
                source_snippet=fact.source_snippet,
            )
        )
    return grounded


def extract_facts_from_document(client: OllamaClient, pages: list[tuple[int, str]]) -> list[GroundedFact]:
    results: list[GroundedFact] = []
    for page_number, page_text in pages:
        results.extend(extract_facts_from_page(client, page_number=page_number, page_text=page_text))
    return results
