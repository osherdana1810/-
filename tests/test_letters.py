from core import letters

PRODUCT = {
    "name": "מכונת כביסה",
    "brand": "Bosch",
    "model": "WAT28",
    "store": "חנות החשמל",
    "price": 2500.0,
    "currency": "ILS",
    "purchase_date": "2025-12-01",
    "warranty_months": 12,
}


def test_whatsapp_contains_receipt_details_and_problem():
    text = letters.whatsapp_message(PRODUCT, "המכונה לא מסתובבת", "דנה")
    for expected in ["מכונת כביסה", "Bosch WAT28", "חנות החשמל", "01/12/2025",
                     "2500 ILS", "12 חודשים", "01/12/2026", "המכונה לא מסתובבת", "דנה"]:
        assert expected in text


def test_email_subject_mentions_product_and_model():
    subject, body = letters.email_draft(PRODUCT, "קוד E21", "דנה")
    assert "מכונת כביסה" in subject and "WAT28" in subject
    assert "קוד E21" in body and "לכבוד שירות הלקוחות" in body


def test_missing_fields_are_left_out_and_placeholders_used():
    text = letters.whatsapp_message({"name": "טוסטר"}, "   ")
    assert "טוסטר" in text
    assert "חנות רכישה" not in text
    assert "[תיאור התקלה]" in text
    assert "[שם מלא]" in text


def test_bad_purchase_date_does_not_crash():
    lines = letters.receipt_details({"name": "x", "purchase_date": "לא תאריך"})
    assert "תאריך רכישה: לא תאריך" in lines
