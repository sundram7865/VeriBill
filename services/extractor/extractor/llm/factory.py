"""Builds the LLM client for a mode: live, record or replay."""

from __future__ import annotations

import redis

from extractor.config import Settings
from extractor.llm.base import LLMClient, LLMNotConfiguredError, LLMRequest, LLMResponse
from extractor.llm.budget import BudgetedClient, MemorySpendStore, RedisSpendStore, SpendStore
from extractor.llm.cache import RecordingClient, ReplayClient, ResponseCache
from extractor.llm.openai_client import OpenAIClient
from extractor.llm.pricing import Pricing

MODES = ("live", "record", "replay")


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


def build_llm_client(settings: Settings, mode: str | None = None) -> LLMClient:
    mode = mode or settings.llm_mode
    if mode not in MODES:
        raise ValueError(f"LLM mode must be one of {MODES}, got '{mode}'")
    cache = ResponseCache(settings.llm_cache_dir)
    if mode == "replay":
        return ReplayClient(cache)
    if not settings.openai_api_key:
        return UnconfiguredClient(f"OPENAI_API_KEY is not set (LLM_MODE={mode})")
    live = OpenAIClient(settings.openai_api_key, settings.llm_timeout_seconds)
    budgeted = BudgetedClient(
        live, _spend_store(settings), Pricing(settings.pricing_path), settings.daily_budget_usd
    )
    return RecordingClient(budgeted, cache) if mode == "record" else budgeted
