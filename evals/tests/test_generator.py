import random
from datetime import date

import pytest

from evals.generator.factory import InvoiceSpec, build_invoice
from evals.generator.formatting import Style, format_amount
from evals.generator.suite import plan_suite
from evals.generator.tricky import MUTATIONS
from extractor.schemas.invoice import Invoice
from extractor.validators.gstin import is_valid_gstin
from extractor.validators.runner import ValidationConfig, validate_invoice

REFERENCE = date(2026, 11, 1)
CONFIG = ValidationConfig(today=REFERENCE)


def _invoice(seed: int, intra: bool = True, n: int = 5, discount=True, round_off=True):
    rng = random.Random(seed)
    return build_invoice(rng, InvoiceSpec(intra, n, discount, round_off, REFERENCE))


def test_same_seed_gives_same_ground_truth():
    assert _invoice(7).ground_truth == _invoice(7).ground_truth


@pytest.mark.parametrize("seed", range(25))
def test_generated_gstins_have_valid_check_characters(seed):
    header = _invoice(seed).ground_truth["header"]
    assert is_valid_gstin(header["supplier_gstin"])
    assert is_valid_gstin(header["buyer_gstin"])


@pytest.mark.parametrize("seed", range(40))
def test_clean_invoices_pass_every_validator(seed):
    invoice = _invoice(
        seed, intra=seed % 2 == 0, n=1 + seed % 12, discount=seed % 3 == 0, round_off=seed % 4 != 0
    )
    issues = validate_invoice(Invoice.model_validate(invoice.ground_truth), CONFIG)
    assert [i for i in issues if i.severity == "error"] == []


@pytest.mark.parametrize("trick", ["wrong_grand_total", "wrong_subtotal", "invalid_gstin"])
def test_tricky_mutations_are_caught_at_expected_paths(trick):
    for seed in range(10):
        invoice = _invoice(seed)
        expected = MUTATIONS[trick](invoice, random.Random(seed))
        issues = validate_invoice(Invoice.model_validate(invoice.ground_truth), CONFIG)
        error_paths = {i.path for i in issues if i.severity == "error"}
        assert error_paths & set(expected), (trick, seed, issues)


def test_prompt_injection_adds_a_note_but_keeps_ground_truth():
    invoice = _invoice(3)
    before = invoice.ground_truth["totals"]["grand_total"]
    assert MUTATIONS["prompt_injection"](invoice, random.Random(1)) == []
    assert invoice.notes and invoice.ground_truth["totals"]["grand_total"] == before


def test_suite_plan_has_150_cases_with_the_promised_mix():
    plans = plan_suite()
    assert len(plans) == 150
    tricks = [p.trick for p in plans]
    assert tricks.count("invalid_gstin") == 10
    assert tricks.count("prompt_injection") == 10
    assert tricks.count("duplicate") == 10
    assert tricks.count("wrong_grand_total") + tricks.count("wrong_subtotal") == 10
    assert len({p.template for p in plans}) == 5
    assert sum(1 for p in plans if p.variant.startswith("scan")) >= 45


def test_indian_amount_grouping():
    style = Style("indian", "", "%d/%m/%Y", "name")
    assert format_amount(12345678.9, style) == "1,23,45,678.90"
    assert format_amount(999.5, style) == "999.50"
    assert format_amount(-0.4, style) == "-0.40"
