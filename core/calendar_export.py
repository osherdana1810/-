"""Build an iCalendar (.ics) reminder that falls 30 days before a warranty ends.

The file imports into Google Calendar, Apple Calendar and Outlook.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from core.letters import receipt_details

REMINDER_DAYS_BEFORE = 30
MAX_LINE_BYTES = 75  # RFC 5545 line length limit, counted in UTF-8 bytes


def reminder_date(end: date) -> date:
    return end - timedelta(days=REMINDER_DAYS_BEFORE)


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> list[str]:
    """Split a long line so no physical line exceeds 75 bytes. Continuations start with a space."""
    parts: list[str] = []
    current = ""
    for ch in line:
        if len((current + ch).encode("utf-8")) > MAX_LINE_BYTES:
            parts.append(current)
            current = " " + ch
        else:
            current += ch
    parts.append(current)
    return parts


def build_reminder_ics(product: dict, end: date, now: datetime | None = None) -> str:
    """Return the .ics text: an all-day event on the reminder date, with receipt details."""
    now = now or datetime.now(timezone.utc)
    start = reminder_date(end)
    next_day = start + timedelta(days=1)
    summary = f"תוקף אחריות פג בקרוב - {product.get('name') or 'מוצר'}"
    description = "\n".join(["פרטי הקבלה:", *receipt_details(product)])

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Warranty Manager//HE//",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uuid.uuid4()}@warranty-manager",
        f"DTSTAMP:{now.strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}",
        "TRANSP:TRANSPARENT",
        f"SUMMARY:{_escape(summary)}",
        f"DESCRIPTION:{_escape(description)}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    folded = [part for line in lines for part in _fold(line)]
    return "\r\n".join(folded) + "\r\n"
