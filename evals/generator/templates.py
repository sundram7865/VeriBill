"""Five invoice templates. Each is configuration over the shared drawing blocks."""

from __future__ import annotations

from dataclasses import dataclass

from evals.generator.formatting import Style
from evals.generator.pdf.table import TableLook


@dataclass(frozen=True)
class Template:
    name: str
    title: str
    header_layout: str
    style: Style
    look: TableLook
    rows_per_page: int
    supports_discount: bool
    supports_round_off: bool
    column_titles: dict[str, str]
    totals_labels: dict[str, str]


_FULL_TITLES = {
    "sno": "#",
    "description": "Description",
    "hsn_sac": "HSN/SAC",
    "quantity": "Qty",
    "unit": "Unit",
    "rate": "Rate",
    "discount": "Disc.",
    "taxable_value": "Taxable",
    "cgst_rate": "CGST%",
    "cgst_amount": "CGST",
    "sgst_rate": "SGST%",
    "sgst_amount": "SGST",
    "igst_rate": "IGST%",
    "igst_amount": "IGST",
}
_SHORT_TITLES = {
    **_FULL_TITLES,
    "description": "Item",
    "hsn_sac": "HSN",
    "rate": "Price",
    "taxable_value": "Amount",
    "cgst_rate": "C.Rate",
    "sgst_rate": "S.Rate",
    "igst_rate": "I.Rate",
}

TEMPLATES: tuple[Template, ...] = (
    Template(
        name="classic",
        title="TAX INVOICE",
        header_layout="classic",
        style=Style("indian", "Rs. ", "%d/%m/%Y", "name_code"),
        look=TableLook(font_size=7.5, row_height=6.5, grid=True),
        rows_per_page=14,
        supports_discount=True,
        supports_round_off=True,
        column_titles=_FULL_TITLES,
        totals_labels={
            "subtotal": "Taxable Value",
            "total_tax": "Total Tax",
            "round_off": "Round Off",
            "grand_total": "Grand Total",
        },
    ),
    Template(
        name="modern",
        title="Tax Invoice",
        header_layout="banner",
        style=Style("western", "INR ", "%d-%b-%Y", "code_name"),
        look=TableLook(font_size=7.5, row_height=7, grid=False),
        rows_per_page=13,
        supports_discount=False,
        supports_round_off=True,
        column_titles=_SHORT_TITLES,
        totals_labels={
            "subtotal": "Sub Total",
            "total_tax": "GST Total",
            "round_off": "Rounding",
            "grand_total": "Total Payable",
        },
    ),
    Template(
        name="compact",
        title="GST INVOICE",
        header_layout="two_column",
        style=Style("plain", "", "%d.%m.%Y", "name"),
        look=TableLook(font_size=7, row_height=5.5, grid=True),
        rows_per_page=16,
        supports_discount=True,
        supports_round_off=False,
        column_titles=_SHORT_TITLES,
        totals_labels={
            "subtotal": "Total Before Tax",
            "total_tax": "Tax Amount",
            "round_off": "Round Off",
            "grand_total": "Invoice Total",
        },
    ),
    Template(
        name="ledger",
        title="Tax Invoice",
        header_layout="two_column",
        style=Style("indian", "Rs. ", "%d %b %Y", "name_code"),
        look=TableLook(font_size=7.5, row_height=6.5, grid=False),
        rows_per_page=14,
        supports_discount=False,
        supports_round_off=True,
        column_titles=_FULL_TITLES,
        totals_labels={
            "subtotal": "Subtotal",
            "total_tax": "Total GST",
            "round_off": "Round Off",
            "grand_total": "Amount Due",
        },
    ),
    Template(
        name="statement",
        title="TAX INVOICE",
        header_layout="banner",
        style=Style("indian", "Rs. ", "%Y-%m-%d", "name_code"),
        look=TableLook(font_size=7.5, row_height=9, grid=True),
        # Few rows per page so 7+ line items always spill onto a second page.
        rows_per_page=6,
        supports_discount=True,
        supports_round_off=True,
        column_titles=_FULL_TITLES,
        totals_labels={
            "subtotal": "Taxable Amount",
            "total_tax": "Total Tax",
            "round_off": "Round Off",
            "grand_total": "Grand Total",
        },
    ),
)

TEMPLATES_BY_NAME = {t.name: t for t in TEMPLATES}
