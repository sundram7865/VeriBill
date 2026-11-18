"""Usage accounting for model calls made during one pipeline run."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from extractor.llm.base import LLMResponse
from extractor.llm.pricing import Pricing


@dataclass(frozen=True)
class CallUsage:
    purpose: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    from_cache: bool
    latency_ms: float

    def to_dict(self) -> dict:
        return asdict(self)


def usage_of(purpose: str, response: LLMResponse, pricing: Pricing) -> CallUsage:
    cost = pricing.cost_usd(response.model, response.tokens_in, response.tokens_out)
    return CallUsage(
        purpose=purpose,
        model=response.model,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        cost_usd=0.0 if math.isnan(cost) else cost,
        from_cache=response.from_cache,
        latency_ms=round(response.latency_ms, 1),
    )
