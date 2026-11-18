"""Group words into visual lines and render layout-preserving text.

Layout-preserving text keeps table columns roughly aligned, which helps the model tell a
"Rate" column from a "Taxable" column without seeing the image.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from extractor.parsing.words import Word

CHARS_PER_LINE = 150  # character grid width used to place words horizontally


@dataclass
class TextLine:
    page: int
    words: list[Word]

    @property
    def y(self) -> float:
        return median(w.mid_y for w in self.words)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


def _cluster_by_y(words: list[Word]) -> list[list[Word]]:
    """Digital text: words whose vertical centres are close belong to the same line."""
    if not words:
        return []
    tolerance = 0.5 * median(w.y1 - w.y0 for w in words)
    lines: list[list[Word]] = []
    for word in sorted(words, key=lambda w: (w.mid_y, w.x0)):
        if lines and abs(word.mid_y - median(w.mid_y for w in lines[-1])) <= tolerance:
            lines[-1].append(word)
        else:
            lines.append([word])
    return lines


def _group_by_ocr_line(words: list[Word]) -> list[list[Word]]:
    """OCR text: trust Tesseract's own line ids, which cope with slight skew."""
    groups: dict[tuple[int, int], list[Word]] = {}
    for word in words:
        groups.setdefault((word.block, word.line), []).append(word)
    return sorted(groups.values(), key=lambda ws: median(w.mid_y for w in ws))


def build_lines(words: list[Word], page: int, from_ocr: bool) -> list[TextLine]:
    groups = _group_by_ocr_line(words) if from_ocr else _cluster_by_y(words)
    return [TextLine(page, sorted(group, key=lambda w: w.x0)) for group in groups]


def render_line(line: TextLine) -> str:
    text = ""
    for word in line.words:
        column = int(word.x0 * CHARS_PER_LINE)
        padding = max(1 if text else 0, column - len(text))
        text += " " * padding + word.text
    return text


def render_layout_text(lines: list[TextLine]) -> str:
    out: list[str] = []
    current_page = None
    for line in lines:
        if line.page != current_page:
            current_page = line.page
            out.append(f"=== Page {current_page} ===")
        out.append(render_line(line))
    return "\n".join(out)
