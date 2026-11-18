"""GeminiClient against a stub SDK client: request mapping, parsing, tokens and errors."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from google.genai import errors

from extractor.config import SERVICE_DIR, load_settings
from extractor.llm.base import LLMError, LLMNotConfiguredError, LLMRequest
from extractor.llm.factory import build_llm_client
from extractor.llm.gemini_client import GeminiClient
from extractor.llm.pricing import Pricing
from extractor.schemas.raw import RepairResponse

ANSWER = '{"fields": [{"path": "totals.grand_total", "value": "1,180.00"}]}'


class StubModels:
    def __init__(self, text: str | None = ANSWER, error: Exception | None = None):
        self.text, self.error, self.calls = text, error, []

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.error:
            raise self.error
        usage = SimpleNamespace(
            prompt_token_count=1200, candidates_token_count=300, thoughts_token_count=100
        )
        return SimpleNamespace(text=self.text, usage_metadata=usage)


def request(effort: str | None = "low") -> LLMRequest:
    return LLMRequest(
        purpose="repair",
        model="gemini-3.5-flash-lite",
        system="rules",
        user="<document>text</document>",
        schema=RepairResponse,
        reasoning_effort=effort,
    )


def test_sends_schema_system_prompt_and_thinking_level():
    models = StubModels()
    response = GeminiClient("key", client=SimpleNamespace(models=models)).complete(request())
    call = models.calls[0]
    assert call["model"] == "gemini-3.5-flash-lite"
    assert call["contents"] == "<document>text</document>"
    config = call["config"]
    assert config.system_instruction == "rules"
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == RepairResponse.model_json_schema()
    assert config.thinking_config.thinking_level.value == "LOW"
    assert config.temperature is None  # not sent unless configured
    assert response.data == {"fields": [{"path": "totals.grand_total", "value": "1,180.00"}]}


def test_thinking_tokens_count_as_output():
    response = GeminiClient("key", client=SimpleNamespace(models=StubModels())).complete(request())
    assert (response.tokens_in, response.tokens_out) == (1200, 400)


def test_output_that_breaks_the_schema_is_an_error():
    stub = SimpleNamespace(models=StubModels(text='{"fields": "not a list"}'))
    with pytest.raises(LLMError, match="schema"):
        GeminiClient("key", client=stub).complete(request())


def test_empty_output_is_an_error():
    with pytest.raises(LLMError, match="no output"):
        GeminiClient("key", client=SimpleNamespace(models=StubModels(text=None))).complete(
            request()
        )


def test_api_errors_become_llm_errors():
    error = errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}})
    stub = SimpleNamespace(models=StubModels(error=error))
    with pytest.raises(LLMError, match="429"):
        GeminiClient("key", client=stub).complete(request())


def test_unknown_reasoning_effort_is_rejected():
    with pytest.raises(LLMError, match="reasoning effort"):
        GeminiClient("key", client=SimpleNamespace(models=StubModels())).complete(request("max"))


def test_factory_uses_gemini_by_default_and_explains_a_missing_key():
    settings = replace(load_settings(), llm_provider="gemini", gemini_api_key=None)
    client = build_llm_client(settings, "live")
    with pytest.raises(LLMNotConfiguredError, match="GEMINI_API_KEY"):
        client.complete(request())


def test_free_tier_models_cost_nothing_on_the_free_tier_only():
    free = Pricing(SERVICE_DIR / "pricing.json", "free")
    paid = Pricing(SERVICE_DIR / "pricing.json", "paid")
    assert free.cost_usd("gemini-3.5-flash-lite", 1_000_000, 1_000_000) == 0.0
    assert paid.cost_usd("gemini-3.5-flash-lite", 1_000_000, 1_000_000) == pytest.approx(2.8)
    # A model without a free tier is still priced on the free billing tier.
    assert free.cost_usd("gpt-6-luna", 1_000_000, 0) == pytest.approx(0.1)
