"""Hard daily spend cap (LLM_DAILY_BUDGET_USD), counted in Redis so restarts don't reset it."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Protocol

from extractor.llm.base import BudgetExceededError, LLMClient, LLMRequest, LLMResponse
from extractor.llm.pricing import Pricing

_KEY_TTL_SECONDS = 2 * 24 * 3600


class SpendStore(Protocol):
    def spent(self, day: str) -> float: ...
    def add(self, day: str, amount: float) -> None: ...


class RedisSpendStore:
    def __init__(self, redis_client):
        self.redis = redis_client

    def spent(self, day: str) -> float:
        value = self.redis.get(f"llm:spend:{day}")
        return float(value) if value else 0.0

    def add(self, day: str, amount: float) -> None:
        key = f"llm:spend:{day}"
        pipe = self.redis.pipeline()
        pipe.incrbyfloat(key, amount)
        pipe.expire(key, _KEY_TTL_SECONDS)
        pipe.execute()


class MemorySpendStore:
    def __init__(self):
        self.totals: dict[str, float] = {}

    def spent(self, day: str) -> float:
        return self.totals.get(day, 0.0)

    def add(self, day: str, amount: float) -> None:
        self.totals[day] = self.totals.get(day, 0.0) + amount


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


class BudgetedClient:
    """Refuses new calls once today's spend reaches the cap; records spend after each call."""

    def __init__(
        self, inner: LLMClient, store: SpendStore, pricing: Pricing, daily_limit_usd: float
    ):
        self.inner, self.store, self.pricing = inner, store, pricing
        self.daily_limit_usd = daily_limit_usd

    def complete(self, request: LLMRequest) -> LLMResponse:
        day = _today()
        spent = self.store.spent(day)
        if spent >= self.daily_limit_usd:
            raise BudgetExceededError(
                f"Daily LLM budget of ${self.daily_limit_usd:.2f} reached "
                f"(spent ${spent:.4f}); new work is refused until 00:00 UTC"
            )
        response = self.inner.complete(request)
        cost = self.pricing.cost_usd(response.model, response.tokens_in, response.tokens_out)
        # An unknown price still has to count against the cap; assume a conservative $0.01.
        self.store.add(day, 0.01 if math.isnan(cost) else cost)
        return response
