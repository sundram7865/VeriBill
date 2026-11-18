"""Builds the LLM client for a provider (gemini | openai) and a mode (live | record | replay)."""

from __future__ import annotations

import redis

from extractor.config import Settings
from extractor.llm.base import LLMClient, LLMNotConfiguredError, LLMRequest, LLMResponse
from extractor.llm.budget import BudgetedClient, MemorySpendStore, RedisSpendStore, SpendStore
from extractor.llm.cache import RecordingClient, ReplayClient, ResponseCache
from extractor.llm.gemini_client import GeminiClient
from extractor.llm.openai_client import OpenAIClient
from extractor.llm.pricing import Pricing

MODES = ("live", "record", "replay")
PROVIDERS = ("gemini", "openai")


class UnconfiguredClient:
    """Stands in when no API key is set: every call fails with a clear configuration error,
    while health checks and replay-based evals keep working."""

    def __init__(self, reason: str):
        self.reason = reason

    def complete(self, request: LLMRequest) -> LLMResponse:
        raise LLMNotConfiguredError(self.reason)


def _spend_store(settings: Settings) -> SpendStore:
    if settings.redis_url:
        return RedisSpendStore(redis.Redis.from_url(settings.redis_url))
    return MemorySpendStore()


def _live_client(settings: Settings, mode: str) -> LLMClient:
    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            return UnconfiguredClient(f"GEMINI_API_KEY is not set (LLM_MODE={mode})")
        return GeminiClient(settings.gemini_api_key, settings.llm_timeout_seconds)
    if not settings.openai_api_key:
        return UnconfiguredClient(f"OPENAI_API_KEY is not set (LLM_MODE={mode})")
    return OpenAIClient(settings.openai_api_key, settings.llm_timeout_seconds)


def build_llm_client(settings: Settings, mode: str | None = None) -> LLMClient:
    mode = mode or settings.llm_mode
    if mode not in MODES:
        raise ValueError(f"LLM mode must be one of {MODES}, got '{mode}'")
    if settings.llm_provider not in PROVIDERS:
        raise ValueError(f"LLM_PROVIDER must be one of {PROVIDERS}, got '{settings.llm_provider}'")
    cache = ResponseCache(settings.llm_cache_dir)
    if mode == "replay":
        return ReplayClient(cache)
    live = _live_client(settings, mode)
    if isinstance(live, UnconfiguredClient):
        return live
    pricing = Pricing(settings.pricing_path, settings.billing_tier)
    budgeted = BudgetedClient(live, _spend_store(settings), pricing, settings.daily_budget_usd)
    return RecordingClient(budgeted, cache) if mode == "record" else budgeted
