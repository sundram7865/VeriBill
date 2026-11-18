"""Line-item table: column layout, row formatting and drawing with page breaks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from evals.generator.formatting import Style, format_amount, format_percent, format_quantity
from evals.generator.pdf.canvas import CONTENT_WIDTH, MARGIN, Canvas


@dataclass(frozen=True)
class Column:
    key: str
    title: str
    width: float
    align: str  # "L" | "R" | "C"


# Fixed widths (mm) for every column except the description, which takes the remainder.
_FIXED_WIDTHS = {
    "sno": 6,
    "hsn_sac": 15,
    "quantity": 10,
    "unit": 11,
    "rate": 16,
    "discount": 14,
    "taxable_value": 19,
    "cgst_rate": 11,
    "cgst_amount": 15,
    "sgst_rate": 11,
    "sgst_amount": 15,
    "igst_rate": 11,
    "igst_amount": 19,
}


def table_columns(titles: dict[str, str], intra_state: bool, with_discount: bool) -> list[Column]:
    keys = ["sno", "description", "hsn_sac", "quantity", "unit", "rate"]
    if with_discount:
        keys.append("discount")
    keys.append("taxable_value")
    keys += (
        ["cgst_rate", "cgst_amount", "sgst_rate", "sgst_amount"]
        if intra_state
        else ["igst_rate", "igst_amount"]
    )
    fixed = sum(_FIXED_WIDTHS[k] for k in keys if k != "description")
    columns = []
    for key in keys:
        width = CONTENT_WIDTH - fixed if key == "description" else _FIXED_WIDTHS[key]
        align = "L" if key in ("description", "unit", "hsn_sac") else "R"
        columns.append(Column(key, titles[key], width, align))
    return columns


def format_row(index: int, line: dict, style: Style) -> dict[str, str]:
    row = {"sno": str(index + 1)}
    for key, value in line.items():
        if value is None:
            row[key] = ""
        elif key in ("description", "hsn_sac", "unit"):
            row[key] = str(value)
        elif key == "quantity":
            row[key] = format_quantity(value)
        elif key.endswith("_rate") and key != "rate":
            row[key] = format_percent(value)
        else:
            row[key] = format_amount(value, style)
    return row


@dataclass(frozen=True)
class TableLook:
    font_size: float
    row_height: float
    grid: bool


def _draw_header(canvas: Canvas, columns: list[Column], y: float, look: TableLook) -> float:
    x = MARGIN
    height = look.row_height + 1
    for col in columns:
        canvas.text(
            x + 0.8,
            y + 1.2,
            col.title,
            size=look.font_size,
            bold=True,
            width=col.width - 1.6,
            align=col.align,
        )
        x += col.width
    if look.grid:
        canvas.box(MARGIN, y, CONTENT_WIDTH, height)
    else:
        canvas.hline(MARGIN, MARGIN + CONTENT_WIDTH, y + height, width=0.4)
    return y + height


def _draw_row(
    canvas: Canvas, columns: list[Column], row: dict[str, str], y: float, look: TableLook
) -> float:
    x = MARGIN
    for col in columns:
        canvas.text(
            x + 0.8,
            y + 1.2,
            row.get(col.key, ""),
            size=look.font_size,
            width=col.width - 1.6,
            align=col.align,
        )
        if look.grid:
            canvas.vline(x, y, y + look.row_height)
        x += col.width
    if look.grid:
        canvas.vline(x, y, y + look.row_height)
        canvas.hline(MARGIN, x, y + look.row_height)
    return y + look.row_height


def draw_table(
    canvas: Canvas,
    columns: list[Column],
    rows: list[dict[str, str]],
    y: float,
    look: TableLook,
    rows_per_page: int,
    on_new_page: Callable[[], float],
) -> float:
    """Draw rows, starting a new page (and repeating the header) after rows_per_page rows."""
    y = _draw_header(canvas, columns, y, look)
    for index, row in enumerate(rows):
        if index > 0 and index % rows_per_page == 0:
            y = _draw_header(canvas, columns, on_new_page(), look)
        y = _draw_row(canvas, columns, row, y, look)
    return y
