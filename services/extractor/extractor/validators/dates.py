"""Invoice date: present, a real ISO date, not in the future, not older than the age window."""

from __future__ import annotations

from datetime import date, datetime

from extractor.validators.issue import Issue, error

PATH = "header.invoice_date"


def validate_invoice_date(raw: str | None, today: date, max_age_days: int) -> list[Issue]:
    if not raw:
        return [error(PATH, "missing", "Invoice date is missing")]
    try:
        value = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return [error(PATH, "date_format", f"'{raw}' is not a valid YYYY-MM-DD date")]
    if value > today:
        return [error(PATH, "date_in_future", f"Invoice date {raw} is in the future")]
    if (today - value).days > max_age_days:
        return [
            error(PATH, "date_too_old", f"Invoice date {raw} is older than {max_age_days} days")
        ]
    return []
