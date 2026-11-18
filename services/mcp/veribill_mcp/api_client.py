"""HTTP client for the VeriBill API. GET only: the server has no way to change anything."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


class ApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    token: str

    @classmethod
    def from_env(cls) -> ApiConfig:
        base_url = os.environ.get("VERIBILL_API_URL", "").rstrip("/")
        token = os.environ.get("VERIBILL_MCP_TOKEN", "")
        if not base_url or not token:
            raise ApiError(
                "Set VERIBILL_API_URL (e.g. http://127.0.0.1:4000/api) and VERIBILL_MCP_TOKEN "
                "(create one with: pnpm mint:mcp-token -- <email>)"
            )
        return cls(base_url, token)


class ApiClient:
    def __init__(self, config: ApiConfig, transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(
            base_url=config.base_url,
            headers={"Authorization": f"Bearer {config.token}"},
            timeout=20.0,
            transport=transport,
        )

    def get(self, path: str, params: dict | None = None) -> dict:
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        response = self._http.get(path, params=clean)
        if response.status_code >= 400:
            try:
                message = response.json()["error"]["message"]
            except (ValueError, KeyError, TypeError):
                message = response.text[:200]
            raise ApiError(f"API {path} returned {response.status_code}: {message}")
        return response.json()
