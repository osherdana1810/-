"""Select products whose warranty needs attention. In-app only for the prototype."""
from __future__ import annotations

from datetime import date

from core.warranty import STATUS_EXPIRED, STATUS_SOON, warranty_end, days_left, status


def enrich(product: dict, today: date, lead_days: int) -> dict:
    """Return a copy of the product with end date, days left and status filled in."""
    purchase = date.fromisoformat(product["purchase_date"]) if product.get("purchase_date") else None
    end = warranty_end(purchase, product.get("warranty_months"))
    return {
        **product,
        "end_date": end,
        "days_left": days_left(end, today),
        "status": status(end, today, lead_days),
    }


def due_reminders(products: list[dict], today: date, lead_days: int) -> list[dict]:
    """Products that are expiring soon or already expired, soonest first."""
    items = [enrich(p, today, lead_days) for p in products]
    due = [p for p in items if p["status"] in (STATUS_SOON, STATUS_EXPIRED)]
    return sorted(due, key=lambda p: p["days_left"])
