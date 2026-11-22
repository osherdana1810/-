from datetime import date

from core.warranty import STATUS_EXPIRED, STATUS_OK, STATUS_SOON, STATUS_UNKNOWN, add_months, days_left, status, warranty_end


def test_add_months_clamps_to_month_end():
    assert add_months(date(2025, 1, 31), 1) == date(2025, 2, 28)


def test_add_months_crosses_year():
    assert add_months(date(2025, 11, 15), 3) == date(2026, 2, 15)


def test_warranty_end_basic():
    assert warranty_end(date(2026, 3, 10), 24) == date(2028, 3, 10)


def test_warranty_end_missing_values():
    assert warranty_end(None, 12) is None
    assert warranty_end(date(2026, 1, 1), None) is None
    assert warranty_end(date(2026, 1, 1), 0) is None


def test_days_left_negative_when_expired():
    assert days_left(date(2026, 1, 1), date(2026, 1, 11)) == -10


def test_status_thresholds():
    today = date(2026, 11, 22)
    assert status(date(2026, 10, 1), today) == STATUS_EXPIRED
    assert status(date(2026, 12, 10), today, lead_days=30) == STATUS_SOON
    assert status(date(2027, 6, 1), today, lead_days=30) == STATUS_OK
    assert status(None, today) == STATUS_UNKNOWN
