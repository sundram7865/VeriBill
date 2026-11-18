"""What the LLM returns: every value as a string, exactly as printed.

The model only reads. Turning "1,23,456.00" into 123456.0 or "15-Mar-2026" into 2026-03-15 is
done by deterministic code (extractor.pipeline.normalize_raw), never by the model.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RawHeader(_Strict):
    supplier_name: str | None
    supplier_gstin: str | None
    buyer_name: str | None
    buyer_gstin: str | None
    invoice_number: str | None
    invoice_date: str | None
    place_of_supply: str | None
    currency: str | None


class RawLineItem(_Strict):
    description: str | None
    hsn_sac: str | None
    quantity: str | None
    unit: str | None
    rate: str | None
    discount: str | None
    taxable_value: str | None
    cgst_rate: str | None
    cgst_amount: str | None
    sgst_rate: str | None
    sgst_amount: str | None
    igst_rate: str | None
    igst_amount: str | None


class RawTotals(_Strict):
    subtotal: str | None
    total_tax: str | None
    round_off: str | None
    grand_total: str | None


class RawInvoice(_Strict):
    header: RawHeader
    line_items: list[RawLineItem]
    totals: RawTotals


class RepairedField(_Strict):
    path: str
    value: str | None


class RepairResponse(_Strict):
    fields: list[RepairedField]
