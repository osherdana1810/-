import json
from datetime import date

from core import letters, reminders, storage
from core.ai_extract import parse_extraction


def test_parse_valid_json_in_prose():
    text = 'Here you go: {"name": "מדיח", "price": "2,499", "purchase_date": "2026-03-01", "warranty_months": 24}'
    out = parse_extraction(text)
    assert out["name"] == "מדיח"
    assert out["price"] == 2499.0
    assert out["purchase_date"] == "2026-03-01"
    assert out["warranty_months"] == 24


def test_parse_missing_and_invalid_fields_become_none():
    out = parse_extraction('{"name": "  ", "purchase_date": "31/12/2026", "warranty_months": -3}')
    assert out["name"] is None
    assert out["purchase_date"] is None
    assert out["warranty_months"] is None
    assert out["price"] is None


def test_parse_garbage_returns_all_none():
    out = parse_extraction("no json here")
    assert all(v is None for v in out.values())


def test_reminders_only_soon_or_expired_soonest_first():
    today = date(2026, 11, 22)
    products = [
        {"id": 1, "name": "ok", "purchase_date": "2026-01-01", "warranty_months": 36},
        {"id": 2, "name": "soon", "purchase_date": "2025-12-01", "warranty_months": 12},
        {"id": 3, "name": "expired", "purchase_date": "2024-01-01", "warranty_months": 12},
        {"id": 4, "name": "unknown", "purchase_date": None, "warranty_months": None},
    ]
    due = reminders.due_reminders(products, today, lead_days=30)
    assert [p["name"] for p in due] == ["expired", "soon"]


def test_letter_is_draft_with_product_details():
    text = letters.draft_letter({"name": "טלוויזיה", "model": "X1", "purchase_date": "2026-01-02"},
                                "המסך מהבהב")
    assert "טלוויזיה" in text and "X1" in text and "המסך מהבהב" in text


def test_save_upload_rejects_bad_extension(tmp_path):
    try:
        storage.save_upload(tmp_path, "virus.exe", b"x")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_save_upload_random_name_and_delete(tmp_path):
    rel, digest = storage.save_upload(tmp_path, "receipt.PDF", b"%PDF-1.4")
    assert rel.endswith(".pdf") and "receipt" not in rel
    assert len(digest) == 64
    assert storage.absolute_path(tmp_path, rel).exists()
    storage.delete_file(tmp_path, rel)
    assert not storage.absolute_path(tmp_path, rel).exists()
