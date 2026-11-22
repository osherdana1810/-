"""SQLite storage for products, documents, AI extractions and usage events."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    store TEXT,
    price REAL,
    currency TEXT DEFAULT 'ILS',
    purchase_date TEXT,
    warranty_months INTEGER,
    room TEXT,
    support_phone TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    file_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    uploaded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    raw_json TEXT NOT NULL,
    confirmed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    product_id INTEGER,
    created_at TEXT NOT NULL
);
"""

PRODUCT_FIELDS = (
    "name", "brand", "model", "store", "price", "currency",
    "purchase_date", "warranty_months", "room", "support_phone", "notes",
)


def connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clean(fields: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in PRODUCT_FIELDS:
        if key not in fields:
            continue
        value = fields[key]
        if isinstance(value, date):
            value = value.isoformat()
        if isinstance(value, str):
            value = value.strip() or None
        out[key] = value
    return out


def add_product(conn: sqlite3.Connection, **fields: Any) -> int:
    data = _clean(fields)
    if not data.get("name"):
        raise ValueError("product name is required")
    data.setdefault("currency", "ILS")
    data["created_at"] = _now()
    cols = ", ".join(data)
    marks = ", ".join("?" for _ in data)
    cur = conn.execute(f"INSERT INTO products ({cols}) VALUES ({marks})", list(data.values()))
    conn.commit()
    log_event(conn, "product_added", cur.lastrowid)
    return int(cur.lastrowid)


def update_product(conn: sqlite3.Connection, product_id: int, **fields: Any) -> None:
    data = _clean(fields)
    if not data:
        return
    sets = ", ".join(f"{k} = ?" for k in data)
    conn.execute(f"UPDATE products SET {sets} WHERE id = ?", [*data.values(), product_id])
    conn.commit()


def get_product(conn: sqlite3.Connection, product_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return dict(row) if row else None


def list_products(conn: sqlite3.Connection, room: str | None = None) -> list[dict]:
    if room:
        rows = conn.execute("SELECT * FROM products WHERE room = ? ORDER BY name", (room,))
    else:
        rows = conn.execute("SELECT * FROM products ORDER BY name")
    return [dict(r) for r in rows.fetchall()]


def list_rooms(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT room FROM products WHERE room IS NOT NULL AND room != '' ORDER BY room"
    )
    return [r["room"] for r in rows.fetchall()]


def delete_product(conn: sqlite3.Connection, product_id: int) -> None:
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()


def add_document(conn: sqlite3.Connection, product_id: int, kind: str,
                 file_path: str, sha256: str) -> int:
    cur = conn.execute(
        "INSERT INTO documents (product_id, kind, file_path, sha256, uploaded_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (product_id, kind, file_path, sha256, _now()),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_documents(conn: sqlite3.Connection, product_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM documents WHERE product_id = ? ORDER BY uploaded_at", (product_id,)
    )
    return [dict(r) for r in rows.fetchall()]


def add_extraction(conn: sqlite3.Connection, document_id: int | None, raw_json: str) -> int:
    cur = conn.execute(
        "INSERT INTO extractions (document_id, raw_json, created_at) VALUES (?, ?, ?)",
        (document_id, raw_json, _now()),
    )
    conn.commit()
    return int(cur.lastrowid)


def log_event(conn: sqlite3.Connection, kind: str, product_id: int | None = None) -> None:
    conn.execute(
        "INSERT INTO events (kind, product_id, created_at) VALUES (?, ?, ?)",
        (kind, product_id, _now()),
    )
    conn.commit()


def count_events(conn: sqlite3.Connection, kind: str) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM events WHERE kind = ?", (kind,)).fetchone()
    return int(row["n"])


def delete_all(conn: sqlite3.Connection) -> None:
    """Remove every row. Uploaded files are removed separately by storage.delete_all_files."""
    conn.executescript(
        "DELETE FROM extractions; DELETE FROM documents; DELETE FROM products; DELETE FROM events;"
    )
    conn.commit()
