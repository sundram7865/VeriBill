"""FastAPI application factory. Run with: uvicorn extractor.main:app"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from extractor.api import extract_route, health
from extractor.api.errors import http_error_handler, pipeline_error_handler
from extractor.config import Settings, load_settings
from extractor.llm.base import LLMClient, LLMError
from extractor.llm.factory import build_llm_client
from extractor.logging_setup import configure_logging
from extractor.pipeline.ingest import IngestError
from extractor.pipeline.parse import ParseError


def create_app(settings: Settings | None = None, llm_client: LLMClient | None = None) -> FastAPI:
    configure_logging()
    settings = settings or load_settings()
    app = FastAPI(title="VeriBill extractor", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.llm_client = llm_client or build_llm_client(settings)
    app.include_router(health.router)
    app.include_router(extract_route.router)
    for exc_type in (IngestError, ParseError, LLMError):
        app.add_exception_handler(exc_type, pipeline_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, http_error_handler)
    return app


app = create_app()
