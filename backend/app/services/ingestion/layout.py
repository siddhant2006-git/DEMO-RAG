import re
import statistics
from dataclasses import dataclass, field

import pdfplumber
import pymupdf

# Headings that mark the section a tender's eligibility/qualification rules live
# in — this is what requirement extraction (Phase 2) chunks around first.
ELIGIBILITY_KEYWORDS = (
    "eligibility",
    "qualification criteria",
    "qualifying criteria",
    "pre-qualification",
    "eligibility criteria",
    "bidder qualification",
)

_NUMBERED_HEADING_RE = re.compile(r"^\s*(\d+(\.\d+)*[.)]?|[A-Z]\.|SECTION\s+[IVXLC\d]+)\s+\S")


@dataclass
class Heading:
    page_number: int
    text: str
    font_size: float
    bbox: list[float]

    @property
    def is_eligibility_section(self) -> bool:
        lowered = self.text.lower()
        return any(keyword in lowered for keyword in ELIGIBILITY_KEYWORDS)


@dataclass
class TableRegion:
    page_number: int
    bbox: list[float]
    row_count: int
    col_count: int


@dataclass
class LayoutAnalysis:
    headings: list[Heading] = field(default_factory=list)
    tables: list[TableRegion] = field(default_factory=list)

    @property
    def eligibility_pages(self) -> list[int]:
        return sorted({h.page_number for h in self.headings if h.is_eligibility_section})


def _is_heading_candidate(text: str, font_size: float, median_size: float) -> bool:
    text = text.strip()
    if not text or len(text) > 120:
        return False
    if font_size >= median_size * 1.15:
        return True
    if text.isupper() and len(text) < 80:
        return True
    if _NUMBERED_HEADING_RE.match(text):
        return True
    return False


def detect_headings(path: str) -> list[Heading]:
    headings: list[Heading] = []

    with pymupdf.open(path) as doc:
        for index, page in enumerate(doc):
            page_dict = page.get_text("dict")
            sizes = [
                span["size"]
                for block in page_dict["blocks"]
                for line in block.get("lines", [])
                for span in line.get("spans", [])
                if span["text"].strip()
            ]
            if not sizes:
                continue
            median_size = statistics.median(sizes)

            for block in page_dict["blocks"]:
                for line in block.get("lines", []):
                    spans = [s for s in line.get("spans", []) if s["text"].strip()]
                    if not spans:
                        continue
                    line_text = "".join(s["text"] for s in spans).strip()
                    max_size = max(s["size"] for s in spans)

                    if _is_heading_candidate(line_text, max_size, median_size):
                        x0 = min(s["bbox"][0] for s in spans)
                        y0 = min(s["bbox"][1] for s in spans)
                        x1 = max(s["bbox"][2] for s in spans)
                        y1 = max(s["bbox"][3] for s in spans)
                        headings.append(
                            Heading(
                                page_number=index + 1,
                                text=line_text,
                                font_size=round(max_size, 1),
                                bbox=[round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                            )
                        )

    return headings


def detect_tables(path: str) -> list[TableRegion]:
    tables: list[TableRegion] = []

    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages):
            for table in page.find_tables():
                rows = table.extract()
                tables.append(
                    TableRegion(
                        page_number=index + 1,
                        bbox=[round(v, 2) for v in table.bbox],
                        row_count=len(rows),
                        col_count=len(rows[0]) if rows else 0,
                    )
                )

    return tables


def analyze_layout(path: str) -> LayoutAnalysis:
    return LayoutAnalysis(headings=detect_headings(path), tables=detect_tables(path))
