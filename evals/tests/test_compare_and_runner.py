import json
from pathlib import Path

from evals.compare import compare
from evals.generate import generate
from evals.metrics.dedupe import dedupe_key
from evals.run import run_suite

VECTORS = Path(__file__).resolve().parents[1] / "fixtures" / "dedupe_vectors.json"


def _report(**summary):
    return {"summary": summary}


def test_compare_flags_drop_beyond_threshold():
    baseline = _report(overall={"f1": 0.90}, validators={"false_alarm_rate": 0.0})
    current = _report(overall={"f1": 0.85}, validators={"false_alarm_rate": 0.0})
    failures = compare(baseline, current, max_drop=0.02)
    assert failures and "overall.f1" in failures[0]


def test_compare_flags_rise_in_lower_is_better_metric():
    baseline = _report(validators={"false_alarm_rate": 0.0})
    current = _report(validators={"false_alarm_rate": 0.10})
    assert compare(baseline, current, max_drop=0.02)


def test_compare_passes_small_noise_and_improvements():
    baseline = _report(overall={"f1": 0.90, "fully_correct_rate": 0.5})
    current = _report(overall={"f1": 0.89, "fully_correct_rate": 0.7})
    assert compare(baseline, current, max_drop=0.02) == []


def test_dedupe_vectors():
    for vector in json.loads(VECTORS.read_text()):
        key = dedupe_key(vector["supplier_gstin"], vector["invoice_number"], vector["grand_total"])
        assert key == vector["key"]


def test_runner_scores_dummy_extractor(tmp_path):
    generate(tmp_path, seed=1, limit=4)
    report = run_suite("dummy", "all", None, max_repairs=0, threshold=0.9, suite_dir=tmp_path)
    summary = report["summary"]
    assert summary["cases"] == 4
    # An empty invoice gets nothing right: recall is 0 and no document is fully correct.
    assert summary["overall"]["recall"] == 0.0
    assert summary["overall"]["fully_correct_rate"] == 0.0
    assert summary["routing"]["auto_approval_rate"] == 0.0
    assert len(report["cases"]) == 4
