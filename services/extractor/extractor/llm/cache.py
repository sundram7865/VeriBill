"""Record and replay LLM responses on disk, keyed by the request hash.

Recordings are only ever written from real model responses (record mode). Replay never
invents an answer: a missing recording is an error.
"""

from __future__ import annotations

import json
from pathlib import Path

from extractor.llm.base import LLMClient, LLMRequest, LLMResponse, ReplayMissError


class ResponseCache:
    def __init__(self, directory: Path):
        self.directory = directory

    def _path(self, key: str) -> Path:
        return self.directory / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict | None:
        path = self._path(key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, key: str, record: dict) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8")


def _to_record(request: LLMRequest, response: LLMResponse) -> dict:
    return {
        "purpose": request.purpose,
        "model": response.model,
        "data": response.data,
        "tokens_in": response.tokens_in,
        "tokens_out": response.tokens_out,
        "latency_ms": round(response.latency_ms, 1),
    }


def _from_record(record: dict) -> LLMResponse:
    return LLMResponse(
        data=record["data"],
        model=record["model"],
        tokens_in=record["tokens_in"],
        tokens_out=record["tokens_out"],
        from_cache=True,
        latency_ms=record.get("latency_ms", 0.0),
    )


class RecordingClient:
    """Calls the live client and saves every response (EVAL_MODE=record)."""

    def __init__(self, inner: LLMClient, cache: ResponseCache):
        self.inner, self.cache = inner, cache

    def complete(self, request: LLMRequest) -> LLMResponse:
        response = self.inner.complete(request)
        self.cache.put(request.cache_key(), _to_record(request, response))
        return response


class ReplayClient:
    """Answers only from recordings (EVAL_MODE=replay). Works offline and costs nothing."""

    def __init__(self, cache: ResponseCache):
        self.cache = cache

    def complete(self, request: LLMRequest) -> LLMResponse:
        record = self.cache.get(request.cache_key())
        if record is None:
            raise ReplayMissError(
                f"No recording for this {request.purpose} request. Run once with "
                "EVAL_MODE=record and an OPENAI_API_KEY to create it."
            )
        return _from_record(record)
