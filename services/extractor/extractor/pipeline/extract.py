"""Node 3, extract: one structured-output LLM call over the layout text."""

from __future__ import annotations

from extractor.llm.base import LLMClient, LLMRequest, LLMResponse
from extractor.prompts import EXTRACT_SYSTEM, build_extract_user
from extractor.schemas.raw import RawInvoice


def extract_raw(
    client: LLMClient,
    model: str,
    document_text: str,
    few_shot: list[dict],
    reasoning_effort: str | None = None,
    temperature: float | None = None,
) -> LLMResponse:
    """Returns the model's as-printed reading of the invoice (schema-validated)."""
    request = LLMRequest(
        purpose="extract",
        model=model,
        system=EXTRACT_SYSTEM,
        user=build_extract_user(document_text, few_shot),
        schema=RawInvoice,
        reasoning_effort=reasoning_effort,
        temperature=temperature,
    )
    response = client.complete(request)
    # Parse again on our side: the schema, not the model, decides what is acceptable.
    RawInvoice.model_validate(response.data)
    return response
