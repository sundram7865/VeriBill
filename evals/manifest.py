"""The suite manifest: one JSON file listing every case, its file and its ground truth."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUITE_DIR = REPO_ROOT / "evals" / "fixtures" / "generated"
MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class Case:
    case_id: str
    file: Path
    mime: str
    split: str
    template: str
    variant: str
    trick: str | None
    duplicate_of: str | None
    pages: int
    expected_issue_paths: list[str]
    ground_truth: dict

    @property
    def is_clean(self) -> bool:
        """Clean = nothing on the document should stop auto-approval."""
        return not self.expected_issue_paths


@dataclass(frozen=True)
class Suite:
    name: str
    reference_date: str
    seed: int
    cases: list[Case]

    def filter(
        self, split: str = "all", limit: int | None = None, variant_prefix: str = ""
    ) -> list[Case]:
        cases = [
            c
            for c in self.cases
            if (split == "all" or c.split == split) and c.variant.startswith(variant_prefix)
        ]
        return cases[:limit] if limit else cases


def load_suite(suite_dir: Path = DEFAULT_SUITE_DIR) -> Suite:
    manifest_path = suite_dir / MANIFEST_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"{manifest_path} not found. Generate the suite first: python -m evals.generate"
        )
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = [
        Case(
            case_id=c["id"],
            file=suite_dir / c["file"],
            mime=c["mime"],
            split=c["split"],
            template=c["template"],
            variant=c["variant"],
            trick=c.get("trick"),
            duplicate_of=c.get("duplicate_of"),
            pages=c["pages"],
            expected_issue_paths=c.get("expected_issue_paths", []),
            ground_truth=c["ground_truth"],
        )
        for c in data["cases"]
    ]
    return Suite(data["suite"], data["reference_date"], data["seed"], cases)
