"""Shared service token check for the internal endpoint. Fails closed when no token is set."""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, Request


def require_service_token(request: Request, authorization: str | None = Header(default=None)):
    expected = request.app.state.settings.service_token
    if not expected:
        raise HTTPException(
            status_code=503,
            detail={"code": "not_configured", "message": "EXTRACTOR_SERVICE_TOKEN is not set"},
        )
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(
            status_code=401, detail={"code": "unauthorized", "message": "Invalid service token"}
        )
