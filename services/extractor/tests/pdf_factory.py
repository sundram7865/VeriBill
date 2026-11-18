"""Builds small synthetic invoice PDFs with PyMuPDF for pipeline tests."""

from __future__ import annotations

import io

import pymupdf
from PIL import Image

# (x in points, text) per row; y advances 18pt per row.
INVOICE_ROWS: list[list[tuple[float, str]]] = [
    [(220, "TAX INVOICE")],
    [(40, "Kaveri Steel Pvt Ltd")],
    [(40, "GSTIN: 27AAPFU0939F1ZV")],
    [(40, "Invoice No: INV/2025-26/0042"), (330, "Invoice Date: 15/03/2026")],
    [(40, "Place of Supply: Maharashtra (27)")],
    [(40, "Bill To: Deccan Foods LLP")],
    [(40, "GSTIN: 29AAACK1234L1ZJ"), (330, "Amounts in INR")],
    [
        (40, "#"),
        (60, "Description"),
        (190, "HSN"),
        (230, "Qty"),
        (260, "Unit"),
        (300, "Rate"),
        (345, "Disc"),
        (385, "Taxable"),
        (440, "CGST%"),
        (480, "CGST"),
        (515, "SGST%"),
        (550, "SGST"),
    ],
    [
        (40, "1"),
        (60, "Copper Wire 2.5 sq mm"),
        (190, "8544"),
        (230, "10"),
        (260, "MTR"),
        (300, "100.00"),
        (345, "0.00"),
        (385, "1,000.00"),
        (440, "9%"),
        (480, "90.00"),
        (515, "9%"),
        (550, "90.00"),
    ],
    [(380, "Taxable Value"), (500, "1,000.00")],
    [(380, "Total Tax"), (500, "180.00")],
    [(380, "Round Off"), (500, "0.00")],
    [(380, "Grand Total"), (500, "Rs. 1,180.00")],
]


def invoice_pdf(extra_rows: list[list[tuple[float, str]]] | None = None, pages: int = 1) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    y = 60.0
    for row in INVOICE_ROWS + (extra_rows or []):
        for x, text in row:
            page.insert_text((x, y), text, fontsize=8)
        y += 18
    for _ in range(pages - 1):
        doc.new_page(width=595, height=842).insert_text((40, 60), "Terms and conditions apply")
    data = doc.tobytes()
    doc.close()
    return data


def blank_pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


def invoice_png() -> bytes:
    with pymupdf.open(stream=invoice_pdf(), filetype="pdf") as doc:
        pix = doc[0].get_pixmap(dpi=200, colorspace=pymupdf.csGRAY)
        image = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
