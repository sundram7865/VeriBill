"""Maps pipeline exceptions to HTTP status codes the API worker can act on.

4xx = the request itself cannot succeed (do not retry); 429 = budget cap; 5xx = may be retried.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from extractor.llm.base import (
    BudgetExceededError,
    LLMError,
    LLMNotConfiguredError,
    ReplayMissError,
)
from extractor.pipeline.ingest import IngestError
from extractor.pipeline.parse import ParseError


def _body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def status_for(exc: Exception) -> tuple[int, str]:
    if isinstance(exc, IngestError):
        return 422, exc.code
    if isinstance(exc, ParseError):
        return 500, exc.code
    if isinstance(exc, BudgetExceededError):
        return 429, "llm_budget_exceeded"
    if isinstance(exc, LLMNotConfiguredError):
        return 503, "llm_not_configured"
    if isinstance(exc, ReplayMissError):
        return 503, "llm_replay_miss"
    if isinstance(exc, LLMError):
        return 502, "llm_error"
    return 500, "internal_error"


async def pipeline_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    status, code = status_for(exc)
    message = str(exc) if status != 500 or code != "internal_error" else "Extraction failed"
    return JSONResponse(status_code=status, content=_body(code, message))


async def http_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Keep one error shape ({"error": {code, message}}) for every failure."""
    status = getattr(exc, "status_code", 500)
    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(status_code=status, content=_body(detail["code"], detail["message"]))
    return JSONResponse(status_code=status, content=_body("bad_request", str(detail or exc)))
