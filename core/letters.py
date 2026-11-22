"""Draft service-customer messages. Drafts only: the user copies and sends them, nothing is sent by the app."""
from __future__ import annotations

from datetime import date

from core.warranty import warranty_end

PLACEHOLDER_PROBLEM = "[תיאור התקלה]"


def _fmt(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value).strftime("%d/%m/%Y")
    except ValueError:
        return value


def receipt_details(product: dict) -> list[str]:
    """Product and purchase facts as 'label: value' lines. Missing facts are left out."""
    lines = [f"מוצר: {product.get('name') or '[שם המוצר]'}"]
    brand_model = " ".join(x for x in [product.get("brand"), product.get("model")] if x)
    if brand_model:
        lines.append(f"יצרן / דגם: {brand_model}")
    if product.get("store"):
        lines.append(f"חנות רכישה: {product['store']}")
    purchase = product.get("purchase_date")
    if purchase:
        lines.append(f"תאריך רכישה: {_fmt(purchase)}")
    if product.get("price"):
        currency = product.get("currency") or "ILS"
        lines.append(f"מחיר: {product['price']:g} {currency}")
    months = product.get("warranty_months")
    if months:
        lines.append(f"תקופת אחריות: {months} חודשים")
        if purchase:
            try:
                end = warranty_end(date.fromisoformat(purchase), months)
                lines.append(f"סיום אחריות: {end.strftime('%d/%m/%Y')}")
            except ValueError:
                pass
    return lines


def whatsapp_message(product: dict, problem: str, sender_name: str = "") -> str:
    issue = problem.strip() or PLACEHOLDER_PROBLEM
    details = "\n".join(f"• {line}" for line in receipt_details(product))
    signature = sender_name.strip() or "[שם מלא]"
    return (
        "שלום, אני פונה לשירות הלקוחות בנוגע לתקלה במוצר שרכשתי.\n\n"
        f"{details}\n\n"
        f"תיאור התקלה: {issue}\n\n"
        "אשמח לתיאום תיקון או החלפה במסגרת האחריות. "
        "קבלה ותעודת אחריות זמינות לפי הצורך.\n\n"
        f"תודה,\n{signature}"
    )


def email_draft(product: dict, problem: str, sender_name: str = "") -> tuple[str, str]:
    """Return (subject, body) for a formal email to customer service."""
    name = product.get("name") or "המוצר"
    model = product.get("model")
    subject = f"פנייה בנוגע לתקלה במוצר {name}" + (f" (דגם {model})" if model else "")
    issue = problem.strip() or PLACEHOLDER_PROBLEM
    details = "\n".join(f"  {line}" for line in receipt_details(product))
    signature = sender_name.strip() or "[שם מלא]"
    body = (
        "לכבוד שירות הלקוחות,\n\n"
        f"ברצוני לפנות אליכם בנוגע לתקלה במוצר שרכשתי. להלן פרטי המוצר והרכישה:\n\n"
        f"{details}\n\n"
        f"תיאור התקלה: {issue}\n\n"
        "אבקש לבדוק את האפשרות לתיקון או החלפה במסגרת האחריות, ולעדכן אותי בשלבים הבאים. "
        "קבלה ותעודת אחריות יצורפו לפי דרישה.\n\n"
        "תודה מראש,\n"
        f"{signature}\n"
    )
    return subject, body


def draft_letter(product: dict, problem: str, sender_name: str = "") -> str:
    """Formal letter text for the product detail page (kept for backward compatibility)."""
    _, body = email_draft(product, problem, sender_name)
    return body
