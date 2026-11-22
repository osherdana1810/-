from datetime import date

import pytest

from core import db


@pytest.fixture()
def conn(tmp_path):
    c = db.connect(tmp_path / "test.db")
    yield c
    c.close()


def test_add_and_get_product(conn):
    pid = db.add_product(conn, name="  מכונת כביסה ", purchase_date=date(2026, 1, 5),
                         warranty_months=24, price=1999.0, room="")
    product = db.get_product(conn, pid)
    assert product["name"] == "מכונת כביסה"
    assert product["purchase_date"] == "2026-01-05"
    assert product["room"] is None
    assert product["currency"] == "ILS"


def test_name_is_required(conn):
    with pytest.raises(ValueError):
        db.add_product(conn, name="   ")


def test_update_and_list_by_room(conn):
    pid = db.add_product(conn, name="טלוויזיה", room="סלון")
    db.add_product(conn, name="מקרר", room="מטבח")
    db.update_product(conn, pid, warranty_months=36)
    assert db.get_product(conn, pid)["warranty_months"] == 36
    assert [p["name"] for p in db.list_products(conn, room="סלון")] == ["טלוויזיה"]
    assert db.list_rooms(conn) == ["מטבח", "סלון"]


def test_documents_cascade_on_delete(conn):
    pid = db.add_product(conn, name="מחשב")
    db.add_document(conn, pid, "receipt", "uploads/a.pdf", "abc")
    db.delete_product(conn, pid)
    assert db.list_documents(conn, pid) == []


def test_events_counted(conn):
    db.add_product(conn, name="א")
    db.add_product(conn, name="ב")
    assert db.count_events(conn, "product_added") == 2


def test_delete_all_clears_everything(conn):
    pid = db.add_product(conn, name="א")
    db.add_document(conn, pid, "receipt", "uploads/a.pdf", "abc")
    db.delete_all(conn)
    assert db.list_products(conn) == []
    assert db.count_events(conn, "product_added") == 0
