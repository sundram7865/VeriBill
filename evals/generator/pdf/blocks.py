"""Header, totals and notes blocks. Each header layout is one function returning the next y."""

from __future__ import annotations

from dataclasses import dataclass

from evals.generator.formatting import Style, format_amount, format_date
from evals.generator.pdf.canvas import CONTENT_WIDTH, MARGIN, PAGE_HEIGHT, PAGE_WIDTH, Canvas


@dataclass(frozen=True)
class HeaderData:
    supplier_name: str
    supplier_address: str
    supplier_gstin: str
    buyer_name: str
    buyer_address: str
    buyer_gstin: str
    invoice_number: str
    invoice_date: str  # ISO; formatted by style
    place_of_supply: str  # already formatted
    currency: str


def _wrap(text: str, max_chars: int) -> list[str]:
    lines, current = [], ""
    for part in text.split(", "):
        candidate = f"{current}, {part}" if current else part
        if len(candidate) > max_chars and current:
            lines.append(current + ",")
            current = part
        else:
            current = candidate
    return [*lines, current]


def _party(
    canvas: Canvas,
    x: float,
    y: float,
    label: str,
    name: str,
    address: str,
    gstin: str,
    width_chars: int = 48,
) -> float:
    canvas.text(x, y, label, size=8, gray=90)
    canvas.text(x, y + 4.5, name, size=10.5, bold=True)
    y += 10
    for line in _wrap(address, width_chars):
        canvas.text(x, y, line, size=8.5)
        y += 4.2
    canvas.text(x, y, f"GSTIN: {gstin}", size=8.5, bold=True)
    return y + 6


def classic_header(canvas: Canvas, data: HeaderData, style: Style, title: str) -> float:
    canvas.text(MARGIN, 12, title, size=14, bold=True, width=CONTENT_WIDTH, align="C")
    y_left = _party(
        canvas,
        MARGIN,
        22,
        "Supplier",
        data.supplier_name,
        data.supplier_address,
        data.supplier_gstin,
    )
    meta = [
        ("Invoice No:", data.invoice_number),
        ("Invoice Date:", format_date(data.invoice_date, style)),
        ("Place of Supply:", data.place_of_supply),
    ]
    y = 26.5
    for label, value in meta:
        canvas.text(120, y, label, size=8.5, bold=True)
        canvas.text(148, y, value, size=8.5)
        y += 5
    y = _party(
        canvas,
        MARGIN,
        max(y_left, y) + 2,
        "Bill To",
        data.buyer_name,
        data.buyer_address,
        data.buyer_gstin,
    )
    canvas.text(MARGIN, y, f"Amounts in {data.currency}", size=8, gray=80)
    return y + 6


def banner_header(canvas: Canvas, data: HeaderData, style: Style, title: str) -> float:
    canvas.text(MARGIN, 12, data.supplier_name, size=15, bold=True)
    canvas.text(
        PAGE_WIDTH - MARGIN - 50, 13, title.upper(), size=11, bold=True, width=50, align="R"
    )
    y = 20
    for line in _wrap(data.supplier_address, 70):
        canvas.text(MARGIN, y, line, size=8.5)
        y += 4.2
    canvas.text(MARGIN, y, f"GSTIN {data.supplier_gstin}", size=8.5, bold=True)
    y += 7
    canvas.hline(MARGIN, PAGE_WIDTH - MARGIN, y, width=0.6)
    y += 3
    cells = [
        ("INVOICE #", data.invoice_number),
        ("DATE", format_date(data.invoice_date, style)),
        ("PLACE OF SUPPLY", data.place_of_supply),
        ("CURRENCY", data.currency),
    ]
    cell_w = CONTENT_WIDTH / len(cells)
    for i, (label, value) in enumerate(cells):
        x = MARGIN + i * cell_w
        canvas.box(x, y, cell_w, 11)
        canvas.text(x + 2, y + 1.5, label, size=7, gray=90)
        canvas.text(x + 2, y + 6, value, size=9, bold=True)
    y = _party(
        canvas,
        MARGIN,
        y + 15,
        "BILLED TO",
        data.buyer_name,
        data.buyer_address,
        data.buyer_gstin,
        width_chars=70,
    )
    return y + 1


def two_column_header(canvas: Canvas, data: HeaderData, style: Style, title: str) -> float:
    canvas.text(MARGIN, 12, title, size=13, bold=True)
    y_left = _party(
        canvas,
        MARGIN,
        22,
        "From:",
        data.supplier_name,
        data.supplier_address,
        data.supplier_gstin,
        width_chars=42,
    )
    y_right = _party(
        canvas,
        110,
        22,
        "To:",
        data.buyer_name,
        data.buyer_address,
        data.buyer_gstin,
        width_chars=42,
    )
    y = max(y_left, y_right) + 2
    meta = [
        ("Invoice Number", data.invoice_number),
        ("Invoice Date", format_date(data.invoice_date, style)),
        ("Place of Supply", data.place_of_supply),
        ("Currency", data.currency),
    ]
    for label, value in meta:
        canvas.text(MARGIN, y, label, size=8.5, bold=True)
        canvas.text(MARGIN + 30, y, f": {value}", size=8.5)
        y += 4.8
    return y + 4


HEADER_LAYOUTS = {
    "classic": classic_header,
    "banner": banner_header,
    "two_column": two_column_header,
}


def continuation_header(canvas: Canvas, invoice_number: str) -> float:
    canvas.text(MARGIN, 12, f"Invoice {invoice_number} (continued)", size=9, bold=True)
    return 20


def draw_totals(
    canvas: Canvas, totals: dict, style: Style, labels: dict[str, str], y: float
) -> float:
    rows = [("subtotal", totals["subtotal"]), ("total_tax", totals["total_tax"])]
    if totals["round_off"] is not None:
        rows.append(("round_off", totals["round_off"]))
    rows.append(("grand_total", totals["grand_total"]))
    x_label, x_value_end = 120, PAGE_WIDTH - MARGIN
    for key, value in rows:
        bold = key == "grand_total"
        canvas.text(x_label, y, labels[key], size=9, bold=bold)
        prefix = style.currency_prefix if key == "grand_total" else ""
        canvas.text(
            x_value_end - 40,
            y,
            prefix + format_amount(value, style),
            size=9,
            bold=bold,
            width=40,
            align="R",
        )
        y += 5.5
    return y + 2


def draw_notes(canvas: Canvas, notes: list[str], y: float) -> float:
    if not notes:
        return y
    canvas.text(MARGIN, y, "Notes:", size=8, bold=True)
    y += 4.2
    for note in notes:
        canvas.text(MARGIN, y, note, size=8)
        y += 4.2
    return y


def draw_page_numbers(canvas: Canvas) -> None:
    total = canvas.page_count
    for number in range(1, total + 1):
        canvas.pdf.page = number
        canvas.text(
            MARGIN,
            PAGE_HEIGHT - 10,
            f"Page {number} of {total}",
            size=7.5,
            width=CONTENT_WIDTH,
            align="R",
            gray=90,
        )
    canvas.pdf.page = total
