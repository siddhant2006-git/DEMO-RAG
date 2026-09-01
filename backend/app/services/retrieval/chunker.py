from dataclasses import dataclass, field

from app.services.ingestion.layout import Heading

# Soft cap on chunk size — long enough for a paragraph or two of eligibility
# text, short enough that embeddings stay meaningful and prompts stay cheap.
MAX_CHUNK_CHARS = 1500


@dataclass
class Chunk:
    text: str
    page_numbers: list[int] = field(default_factory=list)
    heading: str | None = None

    @property
    def page_start(self) -> int:
        return min(self.page_numbers) if self.page_numbers else 0

    @property
    def page_end(self) -> int:
        return max(self.page_numbers) if self.page_numbers else 0


def chunk_document(pages: list[tuple[int, str]], headings: list[Heading]) -> list[Chunk]:
    """Splits page text into section-aware chunks that never lose their page
    number(s) — a chunk boundary opens at every detected heading, and within
    a section, text is broken again only if it exceeds MAX_CHUNK_CHARS (at a
    paragraph boundary where possible), each fragment keeping the pages it
    actually came from.
    """
    headings_by_page: dict[int, list[Heading]] = {}
    for h in headings:
        headings_by_page.setdefault(h.page_number, []).append(h)

    chunks: list[Chunk] = []
    current_text = ""
    current_pages: list[int] = []
    current_heading: str | None = None

    def flush() -> None:
        nonlocal current_text, current_pages, current_heading
        if current_text.strip():
            chunks.append(Chunk(text=current_text.strip(), page_numbers=sorted(set(current_pages)), heading=current_heading))
        current_text, current_pages = "", []

    for page_number, page_text in pages:
        page_headings = {h.text for h in headings_by_page.get(page_number, [])}

        for paragraph in page_text.split("\n"):
            stripped = paragraph.strip()
            if not stripped:
                continue

            if stripped in page_headings:
                flush()
                current_heading = stripped
                continue

            if len(current_text) + len(stripped) + 1 > MAX_CHUNK_CHARS:
                flush()

            current_text = f"{current_text}\n{stripped}".strip()
            current_pages.append(page_number)

    flush()
    return chunks
