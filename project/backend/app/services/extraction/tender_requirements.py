from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_logger
from app.schemas.extraction import ExtractedRequirement, RequirementExtractionResult
from app.services.extraction.snippet_guard import is_snippet_grounded
from app.services.llm.client import OllamaClient
from app.services.llm.json_guard import extract_structured

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parents[1] / "llm" / "prompts" / "requirement_extraction.txt"
_MIN_PAGE_CHARS = 20  # skip pages too sparse to plausibly contain a requirement


@dataclass
class GroundedRequirement:
    page_number: int
    requirement: ExtractedRequirement


def extract_requirements_from_page(
    client: OllamaClient, *, page_number: int, page_text: str
) -> list[ExtractedRequirement]:
    if len(page_text.strip()) < _MIN_PAGE_CHARS:
        return []

    prompt = _PROMPT_PATH.read_text(encoding="utf-8").format(page_number=page_number, page_text=page_text)
    result: RequirementExtractionResult = extract_structured(client, prompt, RequirementExtractionResult)

    grounded: list[ExtractedRequirement] = []
    for req in result.requirements:
        if is_snippet_grounded(req.source_snippet, page_text):
            grounded.append(req)
        else:
            logger.warning(
                "requirement_snippet_not_grounded_dropping",
                page_number=page_number,
                requirement_text=req.text[:120],
            )
    return grounded


def extract_requirements_from_document(
    client: OllamaClient, pages: list[tuple[int, str]]
) -> list[GroundedRequirement]:
    """pages: [(page_number, page_text), ...] in document order."""
    results: list[GroundedRequirement] = []
    for page_number, page_text in pages:
        for req in extract_requirements_from_page(client, page_number=page_number, page_text=page_text):
            results.append(GroundedRequirement(page_number=page_number, requirement=req))
    return results
