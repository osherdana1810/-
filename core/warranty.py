"""Warranty date math and status. Pure functions, easy to test."""
from __future__ import annotations

import calendar
from datetime import date

STATUS_UNKNOWN = "unknown"
STATUS_EXPIRED = "expired"
STATUS_SOON = "soon"
STATUS_OK = "ok"


def add_months(d: date, months: int) -> date:
    """Add months to a date, clamping the day to the end of the target month."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def warranty_end(purchase: date | None, months: int | None) -> date | None:
    if purchase is None or not months or months <= 0:
        return None
    return add_months(purchase, months)


def days_left(end: date | None, today: date) -> int | None:
    if end is None:
        return None
    return (end - today).days


def status(end: date | None, today: date, lead_days: int = 30) -> str:
    left = days_left(end, today)
    if left is None:
        return STATUS_UNKNOWN
    if left < 0:
        return STATUS_EXPIRED
    if left <= lead_days:
        return STATUS_SOON
    return STATUS_OK
