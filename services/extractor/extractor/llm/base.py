"""The LLM client contract. Every implementation takes an LLMRequest and returns an LLMResponse."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel


class LLMError(RuntimeError):
    """The model call failed or returned something that does not fit the schema."""


class BudgetExceededError(LLMError):
    """The daily LLM spend cap has been reached; no new work until tomorrow (UTC)."""


class ReplayMissError(LLMError):
    """Replay mode found no recording for this exact request."""


class LLMNotConfiguredError(LLMError):
    """No API key or model id configured; the service still starts but cannot extract."""


@dataclass(frozen=True)
class LLMRequest:
    purpose: str  # "extract" | "repair"
    model: str
    system: str
    user: str
    schema: type[BaseModel]
    reasoning_effort: str | None = None
    temperature: float | None = None

    def cache_key(self) -> str:
        """Stable hash of everything that can change the answer (prompt, schema, settings)."""
        material = json.dumps(
            {
                "model": self.model,
                "system": self.system,
                "user": self.user,
                "schema": self.schema.model_json_schema(),
                "reasoning_effort": self.reasoning_effort,
                "temperature": self.temperature,
            },
            sort_keys=True,
        )
        return hashlib.sha256(material.encode()).hexdigest()


@dataclass(frozen=True)
class LLMResponse:
    data: dict  # parsed, schema-valid output
    model: str
    tokens_in: int
    tokens_out: int
    from_cache: bool = False
    latency_ms: float = 0.0  # live call time; replay returns the recorded live time


class LLMClient(Protocol):
    def complete(self, request: LLMRequest) -> LLMResponse: ...
