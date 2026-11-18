"""Node 8, output: the response JSON (fields with confidence, page, box and issues)."""

from __future__ import annotations

from extractor.normalize import canonical
from extractor.pipeline.state import PipelineState
from extractor.schemas.contract import ExtractResponse, FieldOut, IssueOut, UsageOut
from extractor.schemas.paths import flatten

PIPELINE_VERSION = "1"


def _display(path: str, value: object) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, float):
        number = canonical(path, value)
        return f"{number:.2f}" if isinstance(number, float) else str(value)
    return str(value)


def build_response(state: PipelineState, latency_ms: int) -> ExtractResponse:
    invoice = state.get("invoice")
    grounding = state.get("grounding", {})
    confidences = state.get("field_confidence", {})
    issues = [IssueOut(**i.to_dict()) for i in state.get("issues", [])]
    issues_by_path: dict[str, list[IssueOut]] = {}
    for issue in issues:
        issues_by_path.setdefault(issue.path, []).append(issue)

    fields = []
    for path, value in flatten(invoice).items() if invoice else []:
        located = grounding.get(path)
        fields.append(
            FieldOut(
                path=path,
                value=_display(path, value),
                confidence=confidences.get(path, 0.0),
                page=located.page if located and located.found else None,
                bbox=list(located.bbox) if located and located.found and located.bbox else None,
                grounded=bool(located and located.found),
                issues=issues_by_path.get(path, []),
            )
        )

    calls = state.get("calls", [])
    metadata = state["metadata"]
    return ExtractResponse(
        document_id=metadata.document_id,
        attempt=metadata.attempt,
        pipeline_version=PIPELINE_VERSION,
        decision=state["decision"],  # type: ignore[arg-type]
        decision_reason=state.get("decision_reason", ""),
        document_confidence=state.get("document_confidence", 0.0),
        required_grounded=state.get("required_grounded", False),
        pages=state.get("page_count", 0),
        used_ocr=bool(state.get("document") and state["document"].used_ocr),
        invoice=invoice,
        fields=fields,
        issues=issues,
        repair_attempts=state.get("repair_attempts", 0),
        model=calls[0].model if calls else None,
        tokens_in=sum(c.tokens_in for c in calls),
        tokens_out=sum(c.tokens_out for c in calls),
        cost_usd=round(sum(c.cost_usd for c in calls), 6),
        latency_ms=latency_ms,
        node_timings=state.get("timings", {}),
        llm_calls=[UsageOut(**c.to_dict()) for c in calls],
    )
