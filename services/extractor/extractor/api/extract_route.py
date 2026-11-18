"""POST /v1/extract: multipart with the file bytes and a JSON metadata part."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError

from extractor.api.auth import require_service_token
from extractor.logging_setup import log_event
from extractor.schemas.contract import ExtractMetadata, ExtractResponse
from extractor.service import deps_from_settings, run_extraction

router = APIRouter()
log = logging.getLogger("extractor.extract")


def _parse_metadata(raw: str) -> ExtractMetadata:
    try:
        return ExtractMetadata.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(
            status_code=400, detail={"code": "bad_metadata", "message": str(exc.errors()[:3])}
        ) from exc


def _read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    data = upload.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail={"code": "file_too_large", "message": "File exceeds the size limit"},
        )
    return data


# A plain `def` endpoint: FastAPI runs it in a worker thread, so CPU-heavy OCR does not block
# the event loop (health checks stay responsive during an extraction).
@router.post(
    "/v1/extract", response_model=ExtractResponse, dependencies=[Depends(require_service_token)]
)
def extract(
    request: Request, file: UploadFile = File(...), metadata: str = Form(...)
) -> ExtractResponse:
    settings = request.app.state.settings
    meta = _parse_metadata(metadata)
    data = _read_limited(file, settings.max_file_bytes)
    deps = deps_from_settings(settings, request.app.state.llm_client)
    result = run_extraction(data, meta, deps)
    # Structured log without document contents (no PII): ids, decision, cost, timings.
    log_event(
        log,
        "extraction finished",
        document_id=meta.document_id,
        attempt=meta.attempt,
        decision=result.decision,
        pages=result.pages,
        repairs=result.repair_attempts,
        cost_usd=result.cost_usd,
        latency_ms=result.latency_ms,
    )
    return result
