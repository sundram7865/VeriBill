"""GST state codes, loaded once from data/gst_state_codes.json (the single source of truth)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_DATA_FILE = Path(__file__).with_name("gst_state_codes.json")


@lru_cache(maxsize=1)
def _load() -> dict:
    return json.loads(_DATA_FILE.read_text(encoding="utf-8"))


def state_names() -> dict[str, str]:
    return {code: entry["name"] for code, entry in _load()["states"].items()}


def is_valid_gstin_state_code(code: str) -> bool:
    data = _load()
    return code in data["states"] and code not in data["not_gstin_prefixes"]


@lru_cache(maxsize=1)
def _name_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for code, entry in _load()["states"].items():
        for name in [entry["name"], *entry["aliases"]]:
            index[_key(name)] = code
    return index


def _key(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower().replace("&", "and"))


def state_code_from_text(text: str | None) -> str | None:
    """'Karnataka (29)', '29-Karnataka', 'KARNATAKA' and '29' all map to '29'."""
    if not text:
        return None
    states = _load()["states"]
    digits = re.findall(r"\b(\d{1,2})\b", text)
    for candidate in digits:
        code = candidate.zfill(2)
        if code in states:
            return code
    letters_only = re.sub(r"[\d()\-:]", " ", text)
    return _name_index().get(_key(letters_only))
