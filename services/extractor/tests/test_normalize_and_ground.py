import pytest

from extractor.grounding.ground import ground_invoice
from extractor.normalize import parse_amount, parse_date, values_equal
from extractor.parsing.document import PageInfo, ParsedDocument
from extractor.parsing.layout import build_lines
from extractor.parsing.words import Word
from extractor.pipeline.normalize_raw import normalize_raw
from tests.factories import make_invoice, raw_dict


@pytest.mark.parametrize(
    "text, value",
    [
        ("Rs. 1,23,456.00", 123456.0),
        ("123456.00/-", 123456.0),
        ("-0.40", -0.4),
        ("(1,000.50)", -1000.5),
        ("INR 99", 99.0),
        ("abc", None),
    ],
)
def test_parse_amount(text, value):
    assert parse_amount(text) == value


@pytest.mark.parametrize(
    "text", ["15/03/2026", "15-03-2026", "15.03.2026", "15-Mar-2026", "15 Mar 2026", "2026-03-15"]
)
def test_parse_date_is_day_first(text):
    assert parse_date(text).isoformat() == "2026-03-15"


def test_values_equal_by_field_type():
    assert values_equal("totals.grand_total", 1180, "1,180.00")
    assert values_equal("header.place_of_supply", "Karnataka (29)", "29-KARNATAKA")
    assert not values_equal("header.invoice_number", "INV-1", "INV-2")


def test_normalize_raw_converts_formats_and_flags_garbage():
    invoice, issues = normalize_raw(raw_dict(totals__grand_total="one thousand"))
    assert invoice.header.invoice_date == "2026-03-15"
    assert invoice.line_items[0].cgst_rate == 9.0
    assert invoice.totals.grand_total is None
    assert [(i.path, i.code) for i in issues] == [("totals.grand_total", "number_format")]


def _doc(rows: list[list[str]]) -> ParsedDocument:
    """One page; each row is a line of words laid out left to right."""
    words = []
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            y = 0.05 + r * 0.03
            words.append(Word(text, 1, 0.05 + c * 0.1, y, 0.12 + c * 0.1, y + 0.015))
    return ParsedDocument(pages=[PageInfo(1, "text")], lines=build_lines(words, 1, False))


def test_grounding_prefers_totals_at_the_end_and_rows_for_line_items():
    doc = _doc(
        [
            ["Kaveri", "Steel", "Pvt", "Ltd"],
            ["1", "Copper", "Wire", "2.5", "sq", "mm", "1,180.00"],
            ["Grand", "Total", "1,180.00"],
        ]
    )
    invoice = make_invoice(line__taxable_value=1180.0)
    grounding = ground_invoice(invoice, doc)
    assert grounding["header.supplier_name"].found
    # Same amount printed twice: the total grounds to the last line, the line item to its row.
    assert grounding["totals.grand_total"].bbox[1] > grounding["line_items.0.taxable_value"].bbox[1]
    assert grounding["line_items.0.description"].found
    assert not grounding["header.supplier_gstin"].found  # not printed in this tiny document
