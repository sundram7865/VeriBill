from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Severity = Literal["error", "warn"]


@dataclass(frozen=True)
class Issue:
    path: str  # field path the issue is attached to, e.g. "totals.grand_total"
    code: str  # stable machine code, e.g. "gstin_checksum"
    severity: Severity
    message: str  # human-readable; shown to reviewers and fed to the repair prompt

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def error(path: str, code: str, message: str) -> Issue:
    return Issue(path=path, code=code, severity="error", message=message)


def warn(path: str, code: str, message: str) -> Issue:
    return Issue(path=path, code=code, severity="warn", message=message)
