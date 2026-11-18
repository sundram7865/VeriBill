"""What kind of value each field holds. Drives normalisation, grounding and comparison."""

from __future__ import annotations

from enum import StrEnum

from extractor.schemas.paths import field_name


class FieldType(StrEnum):
    TEXT = "text"
    GSTIN = "gstin"
    CODE = "code"  # invoice number, HSN/SAC: compared without spaces, case-insensitive
    DATE = "date"
    AMOUNT = "amount"  # rupees
    NUMBER = "number"  # quantities and percent rates
    STATE = "state"  # place of supply, compared as a GST state code
    CURRENCY = "currency"


_TYPES: dict[str, FieldType] = {
    "supplier_name": FieldType.TEXT,
    "buyer_name": FieldType.TEXT,
    "description": FieldType.TEXT,
    "unit": FieldType.TEXT,
    "supplier_gstin": FieldType.GSTIN,
    "buyer_gstin": FieldType.GSTIN,
    "invoice_number": FieldType.CODE,
    "hsn_sac": FieldType.CODE,
    "invoice_date": FieldType.DATE,
    "place_of_supply": FieldType.STATE,
    "currency": FieldType.CURRENCY,
    "quantity": FieldType.NUMBER,
    "cgst_rate": FieldType.NUMBER,
    "sgst_rate": FieldType.NUMBER,
    "igst_rate": FieldType.NUMBER,
}


def field_type(path: str) -> FieldType:
    return _TYPES.get(field_name(path), FieldType.AMOUNT)
