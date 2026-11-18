"""Cost estimates from pricing.json (USD per 1M tokens). Unknown models cost NaN, not 0."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, dict[str, float]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["per_million_tokens"]


class Pricing:
    def __init__(self, path: Path):
        self.table = _load(str(path))

    def cost_usd(self, model: str, tokens_in: int, tokens_out: int) -> float:
        prices = self.table.get(model) or self._by_prefix(model)
        if prices is None:
            # Unknown model: report "not known" rather than pretend it was free.
            return math.nan
        return (tokens_in * prices["input"] + tokens_out * prices["output"]) / 1_000_000

    def _by_prefix(self, model: str) -> dict[str, float] | None:
        """Dated snapshots (e.g. 'gpt-6-luna-2026-05-01') use their base model's price."""
        matches = [name for name in self.table if model.startswith(name + "-")]
        return self.table[max(matches, key=len)] if matches else None
