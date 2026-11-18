"""The invoice schema: what the LLM must return and what ground truth looks like.

Every field is required but nullable. OpenAI strict structured outputs need every key present,
and "null" is how the model says "not on the document" instead of guessing.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Header(_Strict):
    supplier_name: str | None
    supplier_gstin: str | None = Field(description="15-character GSTIN exactly as printed")
    buyer_name: str | None
    buyer_gstin: str | None = Field(description="15-character GSTIN exactly as printed")
    invoice_number: str | None
    invoice_date: str | None = Field(description="ISO date YYYY-MM-DD")
    place_of_supply: str | None = Field(description="Place of supply text as printed")
    currency: str | None = Field(description="ISO currency code, e.g. INR")


class LineItem(_Strict):
    description: str | None
    hsn_sac: str | None = Field(description="HSN or SAC code digits as printed")
    quantity: float | None
    unit: str | None
    rate: float | None = Field(description="Unit price before tax")
    discount: float | None = Field(description="Discount amount for the line, not a percent")
    taxable_value: float | None
    cgst_rate: float | None = Field(description="Percent, e.g. 9 for 9%")
    cgst_amount: float | None
    sgst_rate: float | None = Field(description="Percent, e.g. 9 for 9%")
    sgst_amount: float | None
    igst_rate: float | None = Field(description="Percent, e.g. 18 for 18%")
    igst_amount: float | None


class Totals(_Strict):
    subtotal: float | None = Field(description="Sum of taxable values before tax")
    total_tax: float | None
    round_off: float | None = Field(description="Signed round-off amount; 0 if not printed")
    grand_total: float | None


class Invoice(_Strict):
    header: Header
    line_items: list[LineItem]
    totals: Totals


HEADER_FIELDS: tuple[str, ...] = tuple(Header.model_fields)
LINE_FIELDS: tuple[str, ...] = tuple(LineItem.model_fields)
TOTAL_FIELDS: tuple[str, ...] = tuple(Totals.model_fields)

# Fields that must be present and grounded before a document can be auto-approved.
REQUIRED_PATHS: tuple[str, ...] = (
    "header.supplier_name",
    "header.supplier_gstin",
    "header.invoice_number",
    "header.invoice_date",
    "totals.grand_total",
)


def empty_invoice() -> Invoice:
    return Invoice(
        header=Header(**dict.fromkeys(HEADER_FIELDS)),
        line_items=[],
        totals=Totals(**dict.fromkeys(TOTAL_FIELDS)),
    )
