"""A thin wrapper over fpdf2 with millimetre coordinates and a fixed creation date."""

from __future__ import annotations

from datetime import UTC, datetime

from fpdf import FPDF

PAGE_WIDTH = 210.0
PAGE_HEIGHT = 297.0
MARGIN = 12.0
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN
# A fixed creation date keeps generated PDFs byte-identical across runs (reproducible suite).
FIXED_CREATION_DATE = datetime(2025, 1, 1, tzinfo=UTC)


class Canvas:
    def __init__(self, font: str = "Helvetica") -> None:
        self.pdf = FPDF(unit="mm", format="A4")
        self.pdf.set_auto_page_break(auto=False)
        self.pdf.set_creation_date(FIXED_CREATION_DATE)
        self.pdf.set_margins(MARGIN, MARGIN, MARGIN)
        self.font = font

    @property
    def page_count(self) -> int:
        return self.pdf.page

    def new_page(self) -> None:
        self.pdf.add_page()

    def text(
        self,
        x: float,
        y: float,
        value: str,
        size: float = 9,
        bold: bool = False,
        width: float = 0,
        align: str = "L",
        gray: int = 0,
    ) -> None:
        # Shrink to fit fixed-width cells so neighbouring columns never overlap.
        while width and size > 5 and self.text_width(value, size, bold) > width:
            size -= 0.25
        self.pdf.set_font(self.font, style="B" if bold else "", size=size)
        self.pdf.set_text_color(gray, gray, gray)
        self.pdf.set_xy(x, y)
        self.pdf.cell(w=width, h=size * 0.45, text=value, align=align)

    def text_width(self, value: str, size: float, bold: bool = False) -> float:
        self.pdf.set_font(self.font, style="B" if bold else "", size=size)
        return self.pdf.get_string_width(value)

    def hline(self, x1: float, x2: float, y: float, width: float = 0.2) -> None:
        self.pdf.set_line_width(width)
        self.pdf.line(x1, y, x2, y)

    def vline(self, x: float, y1: float, y2: float, width: float = 0.2) -> None:
        self.pdf.set_line_width(width)
        self.pdf.line(x, y1, x, y2)

    def box(self, x: float, y: float, w: float, h: float, width: float = 0.2) -> None:
        self.pdf.set_line_width(width)
        self.pdf.rect(x, y, w, h)

    def output(self) -> bytes:
        return bytes(self.pdf.output())
