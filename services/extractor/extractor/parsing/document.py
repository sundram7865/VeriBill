"""The parsed document: pages, words with boxes, visual lines and layout text."""

from __future__ import annotations

from dataclasses import dataclass, field

from extractor.parsing.layout import TextLine, render_layout_text
from extractor.parsing.words import Word


@dataclass(frozen=True)
class PageInfo:
    number: int
    source: str  # "text" (digital text layer) or "ocr"
    ocr_confidence: float | None = None  # mean Tesseract word confidence, 0..1


@dataclass
class ParsedDocument:
    pages: list[PageInfo]
    lines: list[TextLine] = field(default_factory=list)

    @property
    def words(self) -> list[Word]:
        return [w for line in self.lines for w in line.words]

    @property
    def layout_text(self) -> str:
        return render_layout_text(self.lines)

    def page_text(self, page: int) -> str:
        return render_layout_text([line for line in self.lines if line.page == page])

    @property
    def is_empty(self) -> bool:
        return not any(line.words for line in self.lines)

    @property
    def used_ocr(self) -> bool:
        return any(p.source == "ocr" for p in self.pages)
