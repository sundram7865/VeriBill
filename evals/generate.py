"""Generate the synthetic suite.

    python -m evals.generate [--out evals/fixtures/generated] [--seed 20261118] [--limit N]

Same seed -> same files and ground truth, so results are comparable across machines.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from evals.generator.suite import generate_case, plan_suite, split_for
from evals.manifest import DEFAULT_SUITE_DIR, MANIFEST_NAME

DEFAULT_SEED = 20261118
# Fixed "today" for the suite so date validators give the same answer whenever evals run.
REFERENCE_DATE = date(2026, 11, 1)
_EXTENSIONS = {"application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpg"}


def generate(out_dir: Path, seed: int, limit: int | None = None) -> Path:
    files_dir = out_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    plans = plan_suite()
    if limit:
        plans = plans[:limit]
    base_invoices: dict = {}
    cases = []
    for plan in plans:
        generated = generate_case(plan, seed, REFERENCE_DATE, base_invoices)
        file_name = f"files/{plan.case_id}.{_EXTENSIONS[generated.mime]}"
        (out_dir / file_name).write_bytes(generated.file_bytes)
        cases.append(
            {
                "id": plan.case_id,
                "file": file_name,
                "mime": generated.mime,
                "split": split_for(plan.case_id),
                "template": plan.template,
                "variant": plan.variant,
                "trick": plan.trick,
                "duplicate_of": plan.duplicate_of,
                "pages": generated.pages,
                "expected_issue_paths": generated.expected_issue_paths,
                "ground_truth": generated.ground_truth,
            }
        )
    manifest = {
        "suite": "synthetic",
        "seed": seed,
        "reference_date": REFERENCE_DATE.isoformat(),
        "cases": cases,
    }
    manifest_path = out_dir / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_SUITE_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    path = generate(args.out, args.seed, args.limit)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
