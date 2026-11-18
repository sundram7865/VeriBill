"""The words layer: every word on every page with a normalised bounding box."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Word:
    text: str
    page: int  # 1-based
    # Box normalised to 0..1 of page width/height, so the UI can draw it at any zoom.
    x0: float
    y0: float
    x1: float
    y1: float
    conf: float = 1.0  # 1.0 for digital text; Tesseract confidence for OCR words
    block: int = 0
    line: int = 0

    @property
    def mid_y(self) -> float:
        return (self.y0 + self.y1) / 2


def union_box(words: list[Word]) -> tuple[float, float, float, float]:
    return (
        min(w.x0 for w in words),
        min(w.y0 for w in words),
        max(w.x1 for w in words),
        max(w.y1 for w in words),
    )
