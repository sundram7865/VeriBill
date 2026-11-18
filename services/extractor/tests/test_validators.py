from datetime import date

import pytest

from extractor.validators.dates import validate_invoice_date
from extractor.validators.gstin import check_character, gstin_problems, is_valid_gstin
from extractor.validators.identifiers import hsn_sac_problem, validate_invoice_number
from extractor.validators.line_math import validate_line_math
from extractor.validators.runner import ValidationConfig, validate_invoice
from extractor.validators.tax_type import validate_tax_type
from extractor.validators.totals import validate_totals
from tests.factories import VALID_GSTIN_KA, make_invoice

TODAY = date(2026, 11, 1)


def codes(issues):
    return {(i.path, i.code) for i in issues}


class TestGstin:
    def test_official_test_vector_passes(self):
        assert check_character("27AAPFU0939F1Z") == "V"
        assert is_valid_gstin("27AAPFU0939F1ZV")

    def test_factory_gstin_is_valid(self):
        assert is_valid_gstin(VALID_GSTIN_KA)

    def test_wrong_check_character_fails(self):
        assert ("gstin_checksum", "GSTIN check character does not match") in gstin_problems(
            "27AAPFU0939F1ZX"
        )

    def test_lowercase_and_spaces_are_normalised(self):
        assert is_valid_gstin("27 aapfu0939f1zv")

    @pytest.mark.parametrize(
        "value, code",
        [
            ("27AAPFU0939F1Z", "gstin_length"),
            ("27AAPFU0939F1AV", "gstin_format"),  # 14th character must be Z
            ("2AAAPFU0939F1ZV", "gstin_format"),
        ],
    )
    def test_format_problems(self, value, code):
        assert gstin_problems(value)[0][0] == code

    def test_invalid_state_code(self):
        first14 = "28AAPFU0939F1Z"  # 28 is not in the official state code master
        problems = gstin_problems(first14 + check_character(first14))
        assert [p[0] for p in problems] == ["gstin_state_code"]

    def test_other_countries_code_is_not_a_gstin_prefix(self):
        first14 = "99AAPFU0939F1Z"
        assert "gstin_state_code" in [
            p[0] for p in gstin_problems(first14 + check_character(first14))
        ]


class TestTaxType:
    def test_intra_state_with_cgst_sgst_is_fine(self):
        assert validate_tax_type(make_invoice(intra=True)) == []

    def test_inter_state_with_igst_is_fine(self):
        invoice = make_invoice(intra=False, header__supplier_gstin="27AAPFU0939F1ZV")
        assert validate_tax_type(invoice) == []

    def test_intra_state_charging_igst_is_an_error(self):
        invoice = make_invoice(intra=False, header__place_of_supply="Maharashtra")
        assert ("line_items.0.igst_amount", "tax_type_mismatch") in codes(
            validate_tax_type(invoice)
        )

    def test_inter_state_charging_cgst_is_an_error(self):
        invoice = make_invoice(intra=True, header__place_of_supply="Karnataka (29)")
        assert ("line_items.0.cgst_amount", "tax_type_mismatch") in codes(
            validate_tax_type(invoice)
        )

    def test_both_igst_and_cgst_is_an_error(self):
        invoice = make_invoice(intra=True, line__igst_rate=18.0, line__igst_amount=180.0)
        assert ("line_items.0.igst_amount", "tax_type_both") in codes(validate_tax_type(invoice))

    def test_unknown_place_of_supply_warns(self):
        issues = validate_tax_type(make_invoice(header__place_of_supply=None))
        assert [i.severity for i in issues] == ["warn"]


class TestLineMath:
    def test_consistent_line_passes(self):
        assert validate_line_math(make_invoice(), tolerance=1.0) == []

    def test_taxable_mismatch(self):
        invoice = make_invoice(line__taxable_value=1500.0)
        assert ("line_items.0.taxable_value", "line_taxable_mismatch") in codes(
            validate_line_math(invoice, 1.0)
        )

    def test_discount_is_subtracted(self):
        invoice = make_invoice(
            line__discount=100.0,
            line__taxable_value=900.0,
            line__cgst_amount=81.0,
            line__sgst_amount=81.0,
        )
        assert validate_line_math(invoice, 1.0) == []

    def test_tax_amount_mismatch(self):
        invoice = make_invoice(line__cgst_amount=95.0)
        assert ("line_items.0.cgst_amount", "line_tax_mismatch") in codes(
            validate_line_math(invoice, 1.0)
        )

    def test_within_one_rupee_tolerance(self):
        assert validate_line_math(make_invoice(line__cgst_amount=90.9), 1.0) == []


class TestTotals:
    def test_consistent_totals_pass(self):
        assert validate_totals(make_invoice(), 1.0) == []

    def test_grand_total_mismatch(self):
        issues = validate_totals(make_invoice(totals__grand_total=1300.0), 1.0)
        assert ("totals.grand_total", "grand_total_mismatch") in codes(issues)

    def test_subtotal_mismatch(self):
        issues = validate_totals(make_invoice(totals__subtotal=1200.0), 1.0)
        assert ("totals.subtotal", "subtotal_mismatch") in codes(issues)

    def test_round_off_is_included(self):
        invoice = make_invoice(
            totals__total_tax=180.4,
            totals__round_off=-0.4,
            totals__grand_total=1180.0,
            line__cgst_amount=90.2,
            line__sgst_amount=90.2,
        )
        assert validate_totals(invoice, 1.0) == []

    def test_large_round_off_warns(self):
        issues = validate_totals(
            make_invoice(totals__round_off=5.0, totals__grand_total=1185.0), 1.0
        )
        assert ("totals.round_off", "round_off_large") in codes(issues)


class TestDates:
    def test_valid_date(self):
        assert validate_invoice_date("2026-03-15", TODAY, 1095) == []

    def test_future_date(self):
        assert validate_invoice_date("2027-01-01", TODAY, 1095)[0].code == "date_in_future"

    def test_too_old(self):
        assert validate_invoice_date("2020-01-01", TODAY, 1095)[0].code == "date_too_old"

    def test_not_a_real_date(self):
        assert validate_invoice_date("2026-02-30", TODAY, 1095)[0].code == "date_format"

    def test_missing(self):
        assert validate_invoice_date(None, TODAY, 1095)[0].code == "missing"


class TestIdentifiers:
    @pytest.mark.parametrize("value", ["INV/2025-26/0042", "A1", "GST-00042"])
    def test_plausible_invoice_numbers(self, value):
        assert validate_invoice_number(value) == []

    @pytest.mark.parametrize("value", ["INV#42", "THIS-NUMBER-IS-TOO-LONG", ""])
    def test_implausible_invoice_numbers(self, value):
        assert validate_invoice_number(value)

    @pytest.mark.parametrize("code", ["8544", "854411", "30049099", "998713"])
    def test_valid_hsn_sac(self, code):
        assert hsn_sac_problem(code) is None

    @pytest.mark.parametrize("code", ["85", "85441", "99871", "ABCD"])
    def test_invalid_hsn_sac(self, code):
        assert hsn_sac_problem(code)


def test_full_validation_of_clean_invoice_has_no_errors():
    issues = validate_invoice(make_invoice(), ValidationConfig(today=TODAY))
    assert [i for i in issues if i.severity == "error"] == []
