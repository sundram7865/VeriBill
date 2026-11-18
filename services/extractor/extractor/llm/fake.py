"""Test double: answers with responses supplied by the test. Never used in production paths."""

from __future__ import annotations

from collections.abc import Callable

from extractor.llm.base import LLMRequest, LLMResponse

Responder = Callable[[LLMRequest], dict]


class FakeLLMClient:
    def __init__(
        self,
        responder: Responder,
        model: str | None = None,
        tokens_in: int = 1000,
        tokens_out: int = 200,
    ):
        self.responder = responder
        self.model = model
        self.tokens_in, self.tokens_out = tokens_in, tokens_out
        self.calls: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        data = request.schema.model_validate(self.responder(request)).model_dump()
        # Like the real API, report the model that was asked for unless told otherwise.
        return LLMResponse(
            data=data,
            model=self.model or request.model,
            tokens_in=self.tokens_in,
            tokens_out=self.tokens_out,
        )
