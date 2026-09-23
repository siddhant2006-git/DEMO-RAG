from dataclasses import dataclass, field

import pymupdf

# Below this many characters of embedded text, a page is treated as scanned
# and handed to the OCR fallback instead of trusted as-is.
LOW_TEXT_CHAR_THRESHOLD = 50


@dataclass
class WordBox:
    text: str
    bbox: list[float]  # [x0, y0, x1, y1]


@dataclass
class PageExtraction:
    page_number: int  # 1-indexed, matches what an officer sees in the PDF viewer
    text: str
    layout: list[WordBox] = field(default_factory=list)
    needs_ocr: bool = False

    @property
    def char_count(self) -> int:
        return len(self.text.strip())


@dataclass
class DocumentExtraction:
    page_count: int
    pages: list[PageExtraction]


def extract_pdf(path: str) -> DocumentExtraction:
    """Extract per-page text and word-level bounding boxes from a digital PDF.

    Pages with under LOW_TEXT_CHAR_THRESHOLD characters of embedded text are
    flagged needs_ocr=True rather than trusted — the caller (services.ingestion)
    is responsible for running the OCR fallback on those pages.
    """
    pages: list[PageExtraction] = []

    with pymupdf.open(path) as doc:
        for index, page in enumerate(doc):
            text = page.get_text("text")
            words = page.get_text("words")  # (x0, y0, x1, y1, word, block, line, word_no)
            layout = [
                WordBox(text=w[4], bbox=[round(w[0], 2), round(w[1], 2), round(w[2], 2), round(w[3], 2)])
                for w in words
            ]

            extraction = PageExtraction(page_number=index + 1, text=text, layout=layout)
            extraction.needs_ocr = extraction.char_count < LOW_TEXT_CHAR_THRESHOLD
            pages.append(extraction)

    return DocumentExtraction(page_count=len(pages), pages=pages)
