"""Compare a results file against a baseline; exit 1 on regression beyond the allowed drop.

python -m evals.compare --baseline evals/baseline.json --current evals/results/<file>.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    path: str  # dotted path inside "summary"
    higher_is_better: bool


CHECKS = (
    Check("overall.f1", True),
    Check("overall.field_exact_match", True),
    Check("overall.fully_correct_rate", True),
    Check("validators.catch_rate", True),
    Check("validators.false_alarm_rate", False),
    Check("routing.auto_approved_accuracy", True),
    Check("adversarial.injection_resistance", True),
)


def _get(summary: dict, path: str) -> float | None:
    node = summary
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, int | float) else None


def compare(baseline: dict, current: dict, max_drop: float) -> list[str]:
    """Return a list of human-readable regressions (empty means pass)."""
    failures = []
    for check in CHECKS:
        before = _get(baseline["summary"], check.path)
        after = _get(current["summary"], check.path)
        if before is None or after is None:
            continue
        delta = after - before if check.higher_is_better else before - after
        if delta < -max_drop:
            failures.append(f"{check.path}: {before:.4f} -> {after:.4f} (allowed drop {max_drop})")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--max-drop", type=float, default=0.02)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    current = json.loads(args.current.read_text(encoding="utf-8"))
    failures = compare(baseline, current, args.max_drop)
    for line in failures:
        print(f"REGRESSION {line}")
    if failures:
        sys.exit(1)
    print("no regression")


if __name__ == "__main__":
    main()
