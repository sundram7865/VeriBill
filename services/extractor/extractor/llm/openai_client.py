"""Live OpenAI client using the Responses API with structured outputs."""

from __future__ import annotations

import time
from typing import Any

import openai

from extractor.llm.base import LLMError, LLMRequest, LLMResponse


class OpenAIClient:
    def __init__(self, api_key: str, timeout_seconds: float = 120.0, max_retries: int = 2):
        self._client = openai.OpenAI(
            api_key=api_key, timeout=timeout_seconds, max_retries=max_retries
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": request.model,
            "input": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            "text_format": request.schema,
            "store": False,
        }
        # Only send sampling/reasoning knobs that were configured: reasoning models reject
        # temperature, and non-reasoning models reject reasoning effort.
        if request.reasoning_effort:
            kwargs["reasoning"] = {"effort": request.reasoning_effort}
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        started = time.perf_counter()
        try:
            response = self._client.responses.parse(**kwargs)
        except openai.OpenAIError as exc:
            raise LLMError(f"OpenAI call failed: {type(exc).__name__}") from exc

        parsed = response.output_parsed
        if parsed is None:
            raise LLMError("Model returned no schema-valid output (refusal or truncation)")
        usage = response.usage
        return LLMResponse(
            data=parsed.model_dump(),
            model=response.model or request.model,
            tokens_in=usage.input_tokens if usage else 0,
            tokens_out=usage.output_tokens if usage else 0,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
