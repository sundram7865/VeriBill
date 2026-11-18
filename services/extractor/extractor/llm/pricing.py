"""Cost estimates from pricing.json (USD per 1M tokens). Unknown models cost NaN, not 0.

On the free billing tier, models listed under "free_tier_models" really cost nothing, so their
calls are recorded at $0 (the daily budget cap then never trips; quotas limit usage instead).
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

BILLING_TIERS = ("free", "paid")


@lru_cache(maxsize=4)
def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Pricing:
    def __init__(self, path: Path, tier: str = "paid"):
        if tier not in BILLING_TIERS:
            raise ValueError(f"billing tier must be one of {BILLING_TIERS}, got '{tier}'")
        data = _load(str(path))
        self.table: dict[str, dict[str, float]] = data["per_million_tokens"]
        self.free_models: set[str] = set(data.get("free_tier_models", []))
        self.tier = tier

    def cost_usd(self, model: str, tokens_in: int, tokens_out: int) -> float:
        if self.tier == "free" and self._base_name(model) in self.free_models:
            return 0.0
        prices = self.table.get(model) or self._by_prefix(model)
        if prices is None:
            # Unknown model: report "not known" rather than pretend it was free.
            return math.nan
        return (tokens_in * prices["input"] + tokens_out * prices["output"]) / 1_000_000

    def _base_name(self, model: str) -> str:
        if model in self.table:
            return model
        matches = [name for name in self.table if model.startswith(name + "-")]
        return max(matches, key=len) if matches else model

    def _by_prefix(self, model: str) -> dict[str, float] | None:
        """Dated snapshots (e.g. 'gpt-6-luna-2026-05-01') use their base model's price."""
        base = self._base_name(model)
        return self.table.get(base)
