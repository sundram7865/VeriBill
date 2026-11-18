"""CI eval gate: run the offline (oracle) suite and fail on regression against the baseline.

    python -m evals.gate [--baseline evals/baseline.json] [--max-drop 0.02]

The oracle run needs no API key and is deterministic, so it can gate every pull request. It
catches regressions in parsing, OCR, grounding, validators and routing. Model-quality
regressions need the live eval (manual workflow) because they need real model outputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evals.compare import compare
from evals.manifest import REPO_ROOT
from evals.run import run_suite

DEFAULT_BASELINE = REPO_ROOT / "evals" / "baseline.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--max-drop", type=float, default=0.02)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "evals" / "results" / "gate.json")
    args = parser.parse_args()

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    meta = baseline["meta"]
    current = run_suite(
        meta["extractor"], meta["split"], None, meta["max_repairs"], meta["threshold"]
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(current, indent=2), encoding="utf-8")
    failures = compare(baseline, current, args.max_drop)
    for line in failures:
        print(f"REGRESSION {line}")
    if failures:
        sys.exit(1)
    print(f"eval gate passed ({meta['extractor']}, split={meta['split']})")


if __name__ == "__main__":
    main()
