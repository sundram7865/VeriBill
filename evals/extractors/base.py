"""What an extractor adapter returns for one case."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from evals.manifest import Case


@dataclass
class Prediction:
    invoice: dict | None
    decision: str  # auto_approve | needs_review | reject | failed
    document_confidence: float = 0.0
    required_grounded: bool = False
    issues: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    repair_attempts: int = 0
    error: str | None = None

    @property
    def has_errors(self) -> bool:
        return any(issue.get("severity") == "error" for issue in self.issues)


class Extractor(Protocol):
    name: str

    def predict(self, case: Case) -> Prediction: ...
