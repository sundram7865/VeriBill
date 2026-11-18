"""Service configuration, read from environment variables only.

Model ids are never hardcoded: EXTRACT_MODEL and REPAIR_MODEL must come from the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SERVICE_DIR = PACKAGE_DIR.parent


def _env_str(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _env_float(name: str, default: float) -> float:
    raw = _env_str(name)
    return float(raw) if raw is not None else default


def _env_int(name: str, default: int) -> int:
    raw = _env_str(name)
    return int(raw) if raw is not None else default


@dataclass(frozen=True)
class Settings:
    service_token: str | None = None
    llm_mode: str = "live"  # live | record | replay
    llm_provider: str = "gemini"  # gemini | openai
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    billing_tier: str = "free"  # free | paid: free-tier Gemini calls cost $0
    extract_model: str | None = None
    repair_model: str | None = None
    reasoning_effort: str | None = None
    temperature: float | None = None
    llm_timeout_seconds: float = 120.0
    llm_cache_dir: Path = SERVICE_DIR / "llm_cache"
    pricing_path: Path = SERVICE_DIR / "pricing.json"
    daily_budget_usd: float = 2.0
    redis_url: str | None = None

    max_file_bytes: int = 10 * 1024 * 1024
    max_pages: int = 20
    ocr_dpi: int = 200
    min_text_chars_per_page: int = 40
    ocr_lang: str = "eng"
    ocr_remove_lines: bool = True

    max_repair_attempts: int = 2
    auto_approve_threshold: float = 0.9
    max_invoice_age_days: int = 3 * 365
    amount_tolerance: float = 1.0

    extra: dict[str, str] = field(default_factory=dict)


def load_settings() -> Settings:
    temperature = _env_str("LLM_TEMPERATURE")
    return Settings(
        service_token=_env_str("EXTRACTOR_SERVICE_TOKEN"),
        llm_mode=_env_str("LLM_MODE", "live") or "live",
        llm_provider=(_env_str("LLM_PROVIDER", "gemini") or "gemini").lower(),
        gemini_api_key=_env_str("GEMINI_API_KEY"),
        openai_api_key=_env_str("OPENAI_API_KEY"),
        billing_tier=(_env_str("LLM_BILLING_TIER", "free") or "free").lower(),
        extract_model=_env_str("EXTRACT_MODEL"),
        repair_model=_env_str("REPAIR_MODEL"),
        reasoning_effort=_env_str("LLM_REASONING_EFFORT"),
        temperature=float(temperature) if temperature is not None else None,
        llm_timeout_seconds=_env_float("LLM_TIMEOUT_SECONDS", 120.0),
        llm_cache_dir=Path(_env_str("LLM_CACHE_DIR", str(SERVICE_DIR / "llm_cache")) or ""),
        pricing_path=Path(_env_str("PRICING_PATH", str(SERVICE_DIR / "pricing.json")) or ""),
        daily_budget_usd=_env_float("LLM_DAILY_BUDGET_USD", 2.0),
        redis_url=_env_str("REDIS_URL"),
        max_file_bytes=int(_env_float("MAX_UPLOAD_MB", 10) * 1024 * 1024),
        max_pages=_env_int("MAX_PAGES", 20),
        ocr_dpi=_env_int("OCR_DPI", 200),
        min_text_chars_per_page=_env_int("MIN_TEXT_CHARS_PER_PAGE", 40),
        ocr_lang=_env_str("OCR_LANG", "eng") or "eng",
        ocr_remove_lines=(_env_str("OCR_REMOVE_LINES", "true") or "true").lower() == "true",
        max_repair_attempts=_env_int("MAX_REPAIR_ATTEMPTS", 2),
        auto_approve_threshold=_env_float("AUTO_APPROVE_THRESHOLD", 0.9),
        max_invoice_age_days=_env_int("MAX_INVOICE_AGE_DAYS", 3 * 365),
        amount_tolerance=_env_float("AMOUNT_TOLERANCE", 1.0),
    )
