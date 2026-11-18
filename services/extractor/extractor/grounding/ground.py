"""Node 4, ground: locate every extracted value in the document.

A value that cannot be found is a grounding failure: either the model hallucinated it or the
text layer/OCR lost it. Either way a human should look before it is trusted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from extractor.grounding.matchers import max_window_words, score
from extractor.grounding.windows import Window, build_windows
from extractor.parsing.document import ParsedDocument
from extractor.schemas.field_types import FieldType, field_type
from extractor.schemas.invoice import Invoice
from extractor.schemas.paths import flatten, line_index

MIN_TEXT_SCORE = 0.85  # fuzzy ratio needed for names and descriptions
MIN_CODE_SCORE = 0.87  # tolerate ~1 OCR confusion in a 15-character GSTIN


@dataclass(frozen=True)
class Grounding:
    path: str
    found: bool
    score: float
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    ocr_conf: float | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["bbox"] = list(self.bbox) if self.bbox else None
        return data


def _threshold(kind: FieldType) -> float:
    if kind in (FieldType.TEXT,):
        return MIN_TEXT_SCORE
    if kind in (FieldType.GSTIN, FieldType.CODE):
        return MIN_CODE_SCORE
    return 1.0


def _preference(path: str, window: Window, row_line: int | None, n_lines: int) -> float:
    """Tie-breaker between equally good matches (e.g. the same amount printed twice)."""
    if row_line is not None:
        # Line-item fields belong on the same visual line as the item's description.
        return -abs(window.line_index - row_line)
    if path.startswith("totals."):
        return window.line_index / max(n_lines, 1)  # totals sit at the end
    return -window.line_index / max(n_lines, 1)  # header fields sit at the start


def _best_window(path, value, windows, row_line, n_lines) -> tuple[Window | None, float]:
    kind = field_type(path)
    limit = max_window_words(kind, value)
    best, best_key = None, (0.0, float("-inf"))
    for window in windows:
        if len(window.words) > limit:
            continue
        s = score(kind, value, window.text)
        if s <= 0:
            continue
        key = (round(s, 3), _preference(path, window, row_line, n_lines))
        if key > best_key:
            best, best_key = window, key
    return best, best_key[0]


def ground_invoice(invoice: Invoice, document: ParsedDocument) -> dict[str, Grounding]:
    windows = build_windows(document.lines)
    n_lines = len(document.lines)
    values = {p: v for p, v in flatten(invoice).items() if v is not None and v != ""}
    results: dict[str, Grounding] = {}
    row_lines: dict[int, int] = {}

    # Descriptions first: they anchor each line item's row for the numeric fields after them.
    ordered = sorted(values, key=lambda p: (not p.endswith(".description"), p))
    for path in ordered:
        index = line_index(path)
        row_line = row_lines.get(index) if index is not None else None
        window, best = _best_window(path, values[path], windows, row_line, n_lines)
        found = window is not None and best >= _threshold(field_type(path))
        if found and path.endswith(".description") and index is not None:
            row_lines[index] = window.line_index  # type: ignore[union-attr]
        results[path] = Grounding(
            path=path,
            found=found,
            score=best if window else 0.0,
            page=window.page if window else None,
            bbox=window.bbox if window else None,
            ocr_conf=window.ocr_conf if window else None,
        )
    return results
