"""How values are printed. Each template picks a style so the suite covers many real formats."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from extractor.data.states import state_names


@dataclass(frozen=True)
class Style:
    amount_grouping: str  # "indian" 1,23,456.78 | "western" 123,456.78 | "plain" 123456.78
    currency_prefix: str  # printed before totals, e.g. "Rs. "
    date_format: str  # strftime format
    place_format: str  # "name" | "name_code" | "code_name"


def _group_indian(integer_part: str) -> str:
    if len(integer_part) <= 3:
        return integer_part
    head, tail = integer_part[:-3], integer_part[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


def format_amount(value: float, style: Style) -> str:
    negative = value < 0
    integer_part, decimals = f"{abs(value):.2f}".split(".")
    if style.amount_grouping == "indian":
        integer_part = _group_indian(integer_part)
    elif style.amount_grouping == "western":
        integer_part = f"{int(integer_part):,}"
    text = f"{integer_part}.{decimals}"
    return f"-{text}" if negative else text


def format_quantity(value: float) -> str:
    return f"{int(value)}" if float(value).is_integer() else f"{value:g}"


def format_percent(value: float) -> str:
    return f"{value:g}%"


def format_date(iso: str, style: Style) -> str:
    return date.fromisoformat(iso).strftime(style.date_format)


def format_place(state_code: str, style: Style) -> str:
    name = state_names()[state_code]
    if style.place_format == "name_code":
        return f"{name} ({state_code})"
    if style.place_format == "code_name":
        return f"{state_code}-{name}"
    return name
