import re

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


def is_snippet_grounded(snippet: str, source_text: str) -> bool:
    """True only if `snippet` appears verbatim in `source_text` (whitespace
    differences ignored). This is the guardrail against LLM hallucination:
    any extracted requirement or fact whose snippet isn't literally in the
    document gets rejected rather than trusted, per the "LLM extracts, never
    decides, and never invents" rule.
    """
    if not snippet or not snippet.strip():
        return False
    return _normalize(snippet) in _normalize(source_text)
