"""POST /v1/extract contract. Mirrored in Zod at apps/api/src/extractor/extractorSchemas.ts;
a contract test on each side checks the two stay in agreement (see contract/README.md)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from extractor.schemas.invoice import Invoice


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FewShotCorrection(_Model):
    field_path: str
    before: str | None
    after: str | None


class FewShotSupplier(_Model):
    supplier_gstin: str
    corrections: list[FewShotCorrection]


class ExtractMetadata(_Model):
    """The JSON part of the multipart request."""

    document_id: str
    attempt: int = Field(ge=1)
    filename: str | None = None
    # Evals pass a fixed "today" so date checks are reproducible; production omits it.
    reference_date: str | None = None
    few_shot: list[FewShotSupplier] = Field(default_factory=list)


class IssueOut(_Model):
    path: str
    code: str
    severity: Literal["error", "warn"]
    message: str


class FieldOut(_Model):
    path: str
    value: str | None
    confidence: float
    page: int | None
    bbox: list[float] | None = Field(description="[x0, y0, x1, y1] as fractions of the page")
    grounded: bool
    issues: list[IssueOut]


class UsageOut(_Model):
    purpose: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    from_cache: bool
    latency_ms: float


class ExtractResponse(_Model):
    document_id: str
    attempt: int
    pipeline_version: str
    decision: Literal["auto_approve", "needs_review", "reject"]
    decision_reason: str
    document_confidence: float
    required_grounded: bool
    pages: int
    used_ocr: bool
    invoice: Invoice | None
    fields: list[FieldOut]
    issues: list[IssueOut]
    repair_attempts: int
    model: str | None
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int
    node_timings: dict[str, int]
    llm_calls: list[UsageOut]


class ErrorBody(_Model):
    code: str
    message: str


class ErrorResponse(_Model):
    error: ErrorBody
