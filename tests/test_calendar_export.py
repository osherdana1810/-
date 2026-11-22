from datetime import date, datetime, timezone

from core.calendar_export import build_reminder_ics, reminder_date

PRODUCT = {
    "name": "מכונת כביסה, דגם X; גרסה 2",
    "brand": "Bosch",
    "purchase_date": "2025-12-01",
    "warranty_months": 12,
    "price": 2500,
}
NOW = datetime(2026, 11, 22, 9, 0, tzinfo=timezone.utc)


def test_reminder_is_30_days_before_end():
    assert reminder_date(date(2026, 12, 1)) == date(2026, 11, 1)


def test_event_is_all_day_on_reminder_date():
    ics = build_reminder_ics(PRODUCT, date(2026, 12, 1), now=NOW)
    assert "DTSTART;VALUE=DATE:20261101" in ics
    assert "DTEND;VALUE=DATE:20261102" in ics


def test_summary_and_escaping():
    ics = build_reminder_ics(PRODUCT, date(2026, 12, 1), now=NOW)
    unfolded = ics.replace("\r\n ", "")
    assert "SUMMARY:תוקף אחריות פג בקרוב - מכונת כביסה\\, דגם X\\; גרסה 2" in unfolded
    assert "סיום אחריות: 01/12/2026" in unfolded
    assert "יצרן / דגם: Bosch" in unfolded


def test_uses_crlf_and_is_wrapped():
    ics = build_reminder_ics(PRODUCT, date(2026, 12, 1), now=NOW)
    assert ics.startswith("BEGIN:VCALENDAR\r\n")
    assert ics.endswith("END:VCALENDAR\r\n")
    for line in ics.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75
