"""Renders a synthetic invoice with a template into PDF bytes."""

from __future__ import annotations

from evals.generator.factory import SyntheticInvoice
from evals.generator.pdf.blocks import (
    HEADER_LAYOUTS,
    HeaderData,
    continuation_header,
    draw_notes,
    draw_page_numbers,
    draw_totals,
)
from evals.generator.pdf.canvas import PAGE_HEIGHT, Canvas
from evals.generator.pdf.table import draw_table, format_row, table_columns
from evals.generator.templates import Template

_TOTALS_BLOCK_HEIGHT = 45
_BENIGN_NOTES = [
    "Goods once sold will not be taken back. Subject to local jurisdiction.",
    "Payment due within 30 days of the invoice date.",
]


def _header_data(invoice: SyntheticInvoice) -> HeaderData:
    header = invoice.ground_truth["header"]
    return HeaderData(
        supplier_name=header["supplier_name"],
        supplier_address=invoice.supplier_address,
        supplier_gstin=header["supplier_gstin"],
        buyer_name=header["buyer_name"],
        buyer_address=invoice.buyer_address,
        buyer_gstin=header["buyer_gstin"],
        invoice_number=header["invoice_number"],
        invoice_date=header["invoice_date"],
        place_of_supply=header["place_of_supply"],
        currency=header["currency"],
    )


def render_pdf(invoice: SyntheticInvoice, template: Template) -> bytes:
    """Draw the invoice. Ground truth must already hold the values exactly as they print."""
    gt = invoice.ground_truth
    canvas = Canvas()
    canvas.new_page()
    y = HEADER_LAYOUTS[template.header_layout](
        canvas, _header_data(invoice), template.style, template.title
    )

    def next_page() -> float:
        canvas.new_page()
        return continuation_header(canvas, gt["header"]["invoice_number"])

    lines = gt["line_items"]
    intra = lines[0]["cgst_rate"] is not None
    with_discount = lines[0]["discount"] is not None
    columns = table_columns(template.column_titles, intra, with_discount)
    rows = [format_row(i, line, template.style) for i, line in enumerate(lines)]
    y = draw_table(canvas, columns, rows, y, template.look, template.rows_per_page, next_page)

    if y + _TOTALS_BLOCK_HEIGHT > PAGE_HEIGHT - 15:
        y = next_page()
    y = draw_totals(canvas, gt["totals"], template.style, template.totals_labels, y + 4)
    draw_notes(canvas, [*_BENIGN_NOTES, *invoice.notes], y + 2)
    draw_page_numbers(canvas)
    return canvas.output()
