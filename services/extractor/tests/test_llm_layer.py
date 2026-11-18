import math

import pytest

from extractor.config import SERVICE_DIR
from extractor.llm.base import BudgetExceededError, LLMRequest, ReplayMissError
from extractor.llm.budget import BudgetedClient, MemorySpendStore
from extractor.llm.cache import RecordingClient, ReplayClient, ResponseCache
from extractor.llm.fake import FakeLLMClient
from extractor.llm.pricing import Pricing
from extractor.schemas.raw import RepairResponse

PRICING = Pricing(SERVICE_DIR / "pricing.json")


def request(user: str = "read this") -> LLMRequest:
    return LLMRequest(
        purpose="repair", model="gpt-6-luna", system="sys", user=user, schema=RepairResponse
    )


def fake() -> FakeLLMClient:
    return FakeLLMClient(
        lambda _req: {"fields": [{"path": "totals.grand_total", "value": "1"}]},
        tokens_in=100_000,
        tokens_out=20_000,
    )


class TestPricing:
    def test_known_model(self):
        assert PRICING.cost_usd("gpt-6-luna", 1_000_000, 1_000_000) == pytest.approx(0.6)

    def test_dated_snapshot_uses_base_price(self):
        assert PRICING.cost_usd("gpt-6-luna-2026-05-01", 1_000_000, 0) == pytest.approx(0.1)

    def test_unknown_model_is_nan_not_free(self):
        assert math.isnan(PRICING.cost_usd("mystery-model", 10, 10))


class TestBudget:
    def test_spend_is_counted_and_cap_enforced(self):
        store = MemorySpendStore()
        # each call: 100k in + 20k out on gpt-6-luna = $0.02
        client = BudgetedClient(fake(), store, PRICING, daily_limit_usd=0.03)
        client.complete(request())
        client.complete(request())  # spent 0.02 < 0.03, allowed
        with pytest.raises(BudgetExceededError):
            client.complete(request())  # spent 0.04 >= 0.03

    def test_zero_budget_refuses_immediately(self):
        client = BudgetedClient(fake(), MemorySpendStore(), PRICING, daily_limit_usd=0)
        with pytest.raises(BudgetExceededError):
            client.complete(request())


class TestRecordReplay:
    def test_replay_returns_exactly_what_was_recorded(self, tmp_path):
        cache = ResponseCache(tmp_path)
        recorded = RecordingClient(fake(), cache).complete(request())
        replayed = ReplayClient(cache).complete(request())
        assert replayed.data == recorded.data
        assert replayed.tokens_in == recorded.tokens_in and replayed.from_cache

    def test_replay_miss_is_an_error_never_an_invented_answer(self, tmp_path):
        with pytest.raises(ReplayMissError):
            ReplayClient(ResponseCache(tmp_path)).complete(request("never recorded"))

    def test_cache_key_changes_with_prompt_and_model(self):
        base = request()
        assert base.cache_key() == request().cache_key()
        assert base.cache_key() != request("different").cache_key()
        other_model = LLMRequest(
            purpose="repair",
            model="gpt-5-nano",
            system="sys",
            user="read this",
            schema=RepairResponse,
        )
        assert base.cache_key() != other_model.cache_key()
