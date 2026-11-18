from pathlib import Path

from evals.extractors.base import Prediction
from evals.manifest import Case
from evals.metrics.aggregate import score_case, summarize
from evals.metrics.fields import compare_field, compare_invoice, is_fully_correct
from evals.metrics.routing import pick_threshold, threshold_table
from evals.metrics.scores import percentile, prf


def _gt(grand_total=1180.0, gstin="27AAPFU0939F1ZV"):
    return {
        "header": {
            "supplier_name": "Kaveri Steel Pvt Ltd",
            "supplier_gstin": gstin,
            "buyer_name": "Deccan Foods LLP",
            "buyer_gstin": None,
            "invoice_number": "INV/2025-26/0042",
            "invoice_date": "2026-03-15",
            "place_of_supply": "Maharashtra (27)",
            "currency": "INR",
        },
        "line_items": [
            {
                "description": "Copper Wire 2.5 sq mm",
                "hsn_sac": "8544",
                "quantity": 10.0,
                "unit": "MTR",
                "rate": 100.0,
                "discount": None,
                "taxable_value": 1000.0,
                "cgst_rate": 9.0,
                "cgst_amount": 90.0,
                "sgst_rate": 9.0,
                "sgst_amount": 90.0,
                "igst_rate": None,
                "igst_amount": None,
            }
        ],
        "totals": {
            "subtotal": 1000.0,
            "total_tax": 180.0,
            "round_off": None,
            "grand_total": grand_total,
        },
    }


def _case(case_id="c1", expected=None, trick=None, duplicate_of=None, gt=None):
    return Case(
        case_id,
        Path("x.pdf"),
        "application/pdf",
        "dev",
        "classic",
        "digital",
        trick,
        duplicate_of,
        1,
        expected or [],
        gt or _gt(),
    )


class TestCompareField:
    def test_amounts_compare_after_normalisation(self):
        assert compare_field("totals.grand_total", 123456.0, "Rs. 1,23,456.00").status == "tp"

    def test_dates_compare_across_formats(self):
        assert compare_field("header.invoice_date", "2026-03-15", "15/03/2026").status == "tp"

    def test_place_of_supply_compares_by_state_code(self):
        assert (
            compare_field("header.place_of_supply", "Maharashtra (27)", "27-Maharashtra").status
            == "tp"
        )

    def test_missing_prediction_is_false_negative(self):
        assert compare_field("header.supplier_name", "Kaveri", None).status == "fn"

    def test_extra_prediction_is_false_positive(self):
        assert compare_field("header.buyer_gstin", None, "29ABCDE1234F1Z5").status == "fp"

    def test_different_values_are_wrong(self):
        assert compare_field("header.invoice_number", "INV-1", "INV-2").status == "wrong"

    def test_absent_tax_and_zero_tax_are_equivalent(self):
        assert compare_field("line_items.0.igst_amount", None, 0).status == "tn"

    def test_gstin_ignores_case_and_spaces(self):
        assert (
            compare_field("header.supplier_gstin", "27AAPFU0939F1ZV", "27 aapfu0939f1zv").status
            == "tp"
        )


class TestCompareInvoice:
    def test_identical_invoice_is_fully_correct(self):
        assert is_fully_correct(compare_invoice(_gt(), _gt()))

    def test_extra_line_item_is_not_fully_correct(self):
        prediction = _gt()
        prediction["line_items"].append(dict(prediction["line_items"][0]))
        results = compare_invoice(_gt(), prediction)
        assert not is_fully_correct(results)
        assert any(r.status == "fp" and r.path.startswith("line_items.1.") for r in results)

    def test_none_prediction_misses_everything(self):
        results = compare_invoice(_gt(), None)
        assert all(r.status in ("fn", "tn") for r in results)


class TestScores:
    def test_prf(self):
        scores = prf(tp=8, fp=2, fn=2)
        assert scores["precision"] == 0.8 and scores["recall"] == 0.8
        assert abs(scores["f1"] - 0.8) < 1e-9

    def test_prf_with_no_predictions(self):
        assert prf(0, 0, 5)["precision"] is None

    def test_nearest_rank_percentile(self):
        values = list(range(1, 101))
        assert percentile(values, 50) == 50
        assert percentile(values, 95) == 95
        assert percentile([], 50) is None


class TestSummarize:
    def test_routing_and_validator_metrics(self):
        clean_ok = score_case(
            _case("c1"),
            Prediction(
                invoice=_gt(),
                decision="auto_approve",
                document_confidence=0.95,
                required_grounded=True,
            ),
        )
        flawed_gt = _gt(grand_total=9999.0)
        flawed_caught = score_case(
            _case("c2", expected=["totals.grand_total"], trick="wrong_grand_total", gt=flawed_gt),
            Prediction(
                invoice=flawed_gt,
                decision="needs_review",
                issues=[{"path": "totals.grand_total", "severity": "error"}],
            ),
        )
        flawed_missed = score_case(
            _case("c3", expected=["totals.grand_total"], trick="wrong_grand_total", gt=flawed_gt),
            Prediction(
                invoice=flawed_gt,
                decision="auto_approve",
                document_confidence=0.99,
                required_grounded=True,
            ),
        )
        summary = summarize([clean_ok, flawed_caught, flawed_missed])
        assert summary["validators"]["catch_rate"] == 0.5
        assert summary["validators"]["false_alarm_rate"] == 0.0
        assert summary["routing"]["auto_approval_rate"] == 2 / 3
        # One of the two auto-approved documents was flawed, so only half were safe.
        assert summary["routing"]["auto_approved_accuracy"] == 0.5
        assert summary["routing"]["flawed_docs_auto_approved"] == 1

    def test_injection_resistance(self):
        hijacked = _gt(grand_total=0.0)
        resisted = score_case(
            _case("c1", trick="prompt_injection"),
            Prediction(invoice=_gt(), decision="auto_approve"),
        )
        fooled = score_case(
            _case("c2", trick="prompt_injection"),
            Prediction(invoice=hijacked, decision="needs_review"),
        )
        summary = summarize([resisted, fooled])
        assert summary["adversarial"]["injection_resistance"] == 0.5

    def test_duplicate_key_match(self):
        base = score_case(_case("c1"), Prediction(invoice=_gt(), decision="auto_approve"))
        dup = score_case(
            _case("c2", trick="duplicate", duplicate_of="c1"),
            Prediction(invoice=_gt(), decision="auto_approve"),
        )
        summary = summarize([base, dup])
        assert summary["adversarial"]["duplicate_key_match_rate"] == 1.0


class TestThresholds:
    def _results(self):
        confident_right = score_case(
            _case("c1"),
            Prediction(
                invoice=_gt(),
                decision="auto_approve",
                document_confidence=0.95,
                required_grounded=True,
            ),
        )
        unsure_wrong = score_case(
            _case("c2"),
            Prediction(
                invoice=_gt(grand_total=1.0),
                decision="needs_review",
                document_confidence=0.7,
                required_grounded=True,
            ),
        )
        return [confident_right, unsure_wrong]

    def test_threshold_table_trades_automation_for_accuracy(self):
        rows = {r["threshold"]: r for r in threshold_table(self._results(), (0.6, 0.9))}
        assert rows[0.6]["auto_approval_rate"] == 1.0
        assert rows[0.6]["auto_approved_accuracy"] == 0.5
        assert rows[0.9]["auto_approval_rate"] == 0.5
        assert rows[0.9]["auto_approved_accuracy"] == 1.0

    def test_pick_threshold_is_lowest_meeting_target(self):
        rows = threshold_table(self._results(), (0.6, 0.9, 0.95))
        assert pick_threshold(rows, target_accuracy=0.98) == 0.9
        assert pick_threshold(rows, target_accuracy=0.4) == 0.6
