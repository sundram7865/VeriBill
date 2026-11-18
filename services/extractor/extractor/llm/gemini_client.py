"""Live Google Gemini client (google-genai SDK) using JSON-schema structured output."""

from __future__ import annotations

import time
from typing import Any

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from extractor.llm.base import LLMError, LLMRequest, LLMResponse

# Free-tier quotas answer 429 when a per-minute limit is hit. The SDK retries those (and
# transient 5xx) with exponential backoff, so a short burst does not fail the document.
_RETRY = types.HttpRetryOptions(
    attempts=5,
    initial_delay=2.0,
    max_delay=60.0,
    http_status_codes=[429, 500, 502, 503, 504],
)

# Our setting uses OpenAI-style effort names; Gemini calls the same idea a thinking level.
_THINKING_LEVELS = {
    "none": "MINIMAL",
    "minimal": "MINIMAL",
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
}


def _optional_settings(request: LLMRequest) -> dict[str, Any]:
    """Only send knobs that were configured, so model defaults apply otherwise."""
    settings: dict[str, Any] = {}
    if request.temperature is not None:
        settings["temperature"] = request.temperature
    if request.reasoning_effort:
        level = _THINKING_LEVELS.get(request.reasoning_effort.lower())
        if level is None:
            raise LLMError(f"Unknown reasoning effort '{request.reasoning_effort}' for Gemini")
        settings["thinking_config"] = types.ThinkingConfig(thinking_level=level)
    return settings


def _token_counts(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return 0, 0
    tokens_in = usage.prompt_token_count or 0
    # Thinking tokens are billed as output tokens, so they count towards the output total.
    tokens_out = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
    return tokens_in, tokens_out


class GeminiClient:
    def __init__(self, api_key: str, timeout_seconds: float = 120.0, client: Any = None):
        self._client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000), retry_options=_RETRY
            ),
        )

    def complete(self, request: LLMRequest) -> LLMResponse:
        config = types.GenerateContentConfig(
            system_instruction=request.system,
            response_mime_type="application/json",
            response_json_schema=request.schema.model_json_schema(),
            **_optional_settings(request),
        )
        started = time.perf_counter()
        try:
            response = self._client.models.generate_content(
                model=request.model, contents=request.user, config=config
            )
        except errors.APIError as exc:
            raise LLMError(f"Gemini call failed: HTTP {exc.code} {exc.status}") from exc

        text = response.text
        if not text:
            raise LLMError("Model returned no output (blocked, refusal or truncation)")
        try:
            parsed = request.schema.model_validate_json(text)
        except ValidationError as exc:
            raise LLMError("Model output did not match the requested schema") from exc
        tokens_in, tokens_out = _token_counts(response)
        return LLMResponse(
            data=parsed.model_dump(),
            model=request.model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
