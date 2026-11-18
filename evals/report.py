"""Markdown tables for docs/EVAL_REPORT.md from one or two results files.

    python -m evals.report evals/results/oracle-all-r2.json \
        [--before evals/results/oracle-all-r0.json] [--target-accuracy 0.98]

Threshold tuning follows the brief: pick the threshold on the dev split, then report what that
threshold does on the held-out test split (whatever the result).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.manifest import DEFAULT_SUITE_DIR, load_suite
from evals.metrics.routing import DEFAULT_THRESHOLDS
from evals.metrics.scores import rate


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _row(cells) -> str:
    return "| " + " | ".join(_fmt(c) for c in cells) + " |"


def _has_errors(case: dict) -> bool:
    return any(i.get("severity") == "error" for i in case["issues"])


def _auto_at(case: dict, threshold: float) -> bool:
    if case["decision"] in ("failed", "reject"):
        return False
    return (
        (not _has_errors(case))
        and case["required_grounded"]
        and (case["document_confidence"] >= threshold)
    )


def split_summary(cases: list[dict], clean: dict[str, bool], expected: dict[str, list]) -> dict:
    auto = [c for c in cases if c["decision"] == "auto_approve"]
    flawed = [c for c in cases if expected[c["id"]]]
    caught = sum(
        1
        for c in flawed
        if any(i["severity"] == "error" and i["path"] in expected[c["id"]] for i in c["issues"])
    )
    latencies = sorted(c["latency_ms"] for c in cases)
    return {
        "cases": len(cases),
        "fully_correct_rate": rate(sum(c["fully_correct"] for c in cases), len(cases)),
        "auto_approval_rate": rate(len(auto), len(cases)),
        "auto_approved_accuracy": rate(
            sum(1 for c in auto if c["fully_correct"] and clean[c["id"]]), len(auto)
        ),
        "flawed_auto_approved": sum(1 for c in auto if not clean[c["id"]]),
        "validator_catch_rate": rate(caught, len(flawed)),
        "failed": sum(1 for c in cases if c["decision"] == "failed"),
        "p50_ms": latencies[len(latencies) // 2] if latencies else None,
    }


def threshold_rows(cases: list[dict], clean: dict[str, bool]) -> list[dict]:
    rows = []
    for t in DEFAULT_THRESHOLDS:
        auto = [c for c in cases if _auto_at(c, t)]
        rows.append(
            {
                "threshold": t,
                "auto_approval_rate": rate(len(auto), len(cases)),
                "auto_approved_accuracy": rate(
                    sum(1 for c in auto if c["fully_correct"] and clean[c["id"]]), len(auto)
                ),
                "auto_approved": len(auto),
            }
        )
    return rows


def pick(rows: list[dict], target: float) -> float | None:
    for row in rows:
        acc = row["auto_approved_accuracy"]
        if row["auto_approved"] and acc is not None and acc >= target:
            return row["threshold"]
    return None


def render(report: dict, before: dict | None, target: float, suite_dir: Path) -> str:
    suite = load_suite(suite_dir)
    clean = {c.case_id: c.is_clean for c in suite.cases}
    expected = {c.case_id: c.expected_issue_paths for c in suite.cases}
    cases = report["cases"]
    by_split = {s: [c for c in cases if c["split"] == s] for s in ("dev", "test")}
    meta = report["meta"]
    out = [
        f"Command: `{meta['command']}` (extractor={meta['extractor']}, "
        f"max_repairs={meta['max_repairs']}, threshold={meta['threshold']})",
        "",
    ]

    out += [
        "| split | cases | fully correct | auto-approval | auto-approved accuracy | "
        "flawed auto-approved | validator catch rate | failed | p50 ms |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, group in [("dev", by_split["dev"]), ("test", by_split["test"]), ("all", cases)]:
        s = split_summary(group, clean, expected)
        out.append(
            _row(
                [
                    name,
                    s["cases"],
                    s["fully_correct_rate"],
                    s["auto_approval_rate"],
                    s["auto_approved_accuracy"],
                    s["flawed_auto_approved"],
                    s["validator_catch_rate"],
                    s["failed"],
                    s["p50_ms"],
                ]
            )
        )

    dev_rows = threshold_rows(by_split["dev"], clean)
    test_rows = {r["threshold"]: r for r in threshold_rows(by_split["test"], clean)}
    chosen = pick(dev_rows, target)
    out += [
        "",
        f"Threshold table (target auto-approved accuracy {target:.2f} on dev; "
        f"chosen on dev: {_fmt(chosen)})",
        "",
        "| threshold | dev auto-approval | dev accuracy | test auto-approval | test accuracy |",
        "|---|---|---|---|---|",
    ]
    for row in dev_rows:
        t = test_rows[row["threshold"]]
        out.append(
            _row(
                [
                    row["threshold"],
                    row["auto_approval_rate"],
                    row["auto_approved_accuracy"],
                    t["auto_approval_rate"],
                    t["auto_approved_accuracy"],
                ]
            )
        )

    if before:
        out += [
            "",
            "Before vs after the repair loop (all cases):",
            "",
            "| run | max repairs | fully correct | auto-approval | validator catch rate |",
            "|---|---|---|---|---|",
        ]
        for label, r in (("before", before), ("after", report)):
            s = split_summary(r["cases"], clean, expected)
            out.append(
                _row(
                    [
                        label,
                        r["meta"]["max_repairs"],
                        s["fully_correct_rate"],
                        s["auto_approval_rate"],
                        s["validator_catch_rate"],
                    ]
                )
            )
    return "\n".join(out)


def variant_table(report: dict) -> str:
    """Per-variant rows straight from the run summary (digital vs each scan degradation)."""
    out = ["| variant | cases | grounded fields | auto-approval |", "|---|---|---|---|"]
    for variant, row in report["summary"]["by_variant"].items():
        out.append(
            _row([variant, row["cases"], row["grounded_field_rate"], row["auto_approval_rate"]])
        )
    return "\n".join(out)


def ablation_table(with_feature: dict, without_feature: dict, label: str) -> str:
    """The same cases with a feature on and off, compared per variant."""
    on, off = with_feature["summary"]["by_variant"], without_feature["summary"]["by_variant"]
    out = [
        f"| variant | cases | grounded fields, {label} off | grounded fields, {label} on | "
        f"auto-approval, {label} off | auto-approval, {label} on |",
        "|---|---|---|---|---|---|",
    ]
    for variant, row_off in off.items():
        row_on = on.get(variant)
        if row_on:
            out.append(
                _row(
                    [
                        variant,
                        row_off["cases"],
                        row_off["grounded_field_rate"],
                        row_on["grounded_field_rate"],
                        row_off["auto_approval_rate"],
                        row_on["auto_approval_rate"],
                    ]
                )
            )
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--before", type=Path, default=None)
    parser.add_argument("--target-accuracy", type=float, default=0.98)
    parser.add_argument("--suite-dir", type=Path, default=DEFAULT_SUITE_DIR)
    parser.add_argument(
        "--ablation-off", type=Path, default=None, help="same cases with a feature turned off"
    )
    parser.add_argument("--ablation-label", default="line removal")
    args = parser.parse_args()
    report = json.loads(args.results.read_text(encoding="utf-8"))
    before = json.loads(args.before.read_text(encoding="utf-8")) if args.before else None
    print(render(report, before, args.target_accuracy, args.suite_dir))
    print("\nPer variant:\n")
    print(variant_table(report))
    if args.ablation_off:
        off = json.loads(args.ablation_off.read_text(encoding="utf-8"))
        print(f"\nAblation ({args.ablation_label}):\n")
        print(ablation_table(report, off, args.ablation_label))


if __name__ == "__main__":
    main()
