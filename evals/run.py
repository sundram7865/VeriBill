"""Run an extractor over the suite and write a results file.

    python -m evals.run --suite synthetic --extractor oracle --split test \
        --out evals/results/<timestamp>.json

EVAL_MODE (live | record | replay, default replay) controls the LLM client for the 'pipeline'
extractor. Without OPENAI_API_KEY only replay (from saved recordings) can run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from evals.extractors.registry import EXTRACTORS, build_extractor
from evals.manifest import DEFAULT_SUITE_DIR, REPO_ROOT, load_suite
from evals.metrics.aggregate import CaseResult, score_case, summarize
from evals.metrics.routing import threshold_table

RESULTS_DIR = REPO_ROOT / "evals" / "results"
CORRECTIONS_SUITE_DIR = REPO_ROOT / "evals" / "fixtures" / "corrections"


def _case_record(result: CaseResult) -> dict:
    p = result.prediction
    return {
        "id": result.case.case_id,
        "split": result.case.split,
        "template": result.case.template,
        "variant": result.case.variant,
        "trick": result.case.trick,
        "decision": p.decision,
        "document_confidence": round(p.document_confidence, 4),
        "required_grounded": p.required_grounded,
        "fully_correct": result.fully_correct,
        "wrong_fields": result.wrong_paths(),
        "issues": p.issues,
        "repair_attempts": p.repair_attempts,
        "cost_usd": p.cost_usd,
        "latency_ms": round(p.latency_ms, 1),
        "error": p.error,
        "prediction": p.invoice,
    }


def run_suite(
    extractor_name: str,
    split: str,
    limit: int | None,
    max_repairs: int,
    threshold: float,
    suite_dir: Path = DEFAULT_SUITE_DIR,
    variant: str = "",
) -> dict:
    suite = load_suite(suite_dir)
    extractor = build_extractor(extractor_name, suite, max_repairs, threshold)
    results = []
    for case in suite.filter(split, limit, variant):
        results.append(score_case(case, extractor.predict(case)))
    return {
        "meta": {
            "suite": suite.name,
            "extractor": extractor_name,
            "eval_mode": os.environ.get("EVAL_MODE", "replay")
            if extractor_name == "pipeline"
            else None,
            "split": split,
            "variant": variant or "all",
            "max_repairs": max_repairs,
            "threshold": threshold,
            "reference_date": suite.reference_date,
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "command": "python -m evals.run " + " ".join(sys.argv[1:]),
        },
        "summary": summarize(results),
        "threshold_table": threshold_table(results),
        "cases": [_case_record(r) for r in results],
    }


def default_out_path(extractor: str, split: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return RESULTS_DIR / f"{stamp}-{extractor}-{split}.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--suite", default="synthetic", choices=["synthetic", "corrections"])
    parser.add_argument("--suite-dir", type=Path, default=None)
    parser.add_argument("--variant", default="", help="only cases whose variant starts with this")
    parser.add_argument("--extractor", default="pipeline", choices=EXTRACTORS)
    parser.add_argument("--split", default="all", choices=["all", "dev", "test"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-repairs", type=int, default=2)
    parser.add_argument(
        "--threshold", type=float, default=float(os.environ.get("AUTO_APPROVE_THRESHOLD", "0.9"))
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    suite_dir = args.suite_dir or (
        CORRECTIONS_SUITE_DIR if args.suite == "corrections" else DEFAULT_SUITE_DIR
    )
    report = run_suite(
        args.extractor,
        args.split,
        args.limit,
        args.max_repairs,
        args.threshold,
        suite_dir,
        args.variant,
    )
    out = args.out or default_out_path(args.extractor, args.split)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    overall = report["summary"]["overall"]
    print(
        json.dumps(
            {"out": str(out), "overall": overall, "routing": report["summary"]["routing"]}, indent=2
        )
    )


if __name__ == "__main__":
    main()
