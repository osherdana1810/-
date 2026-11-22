"""Draft a service-request letter. Draft only: the user copies it; nothing is sent."""
from __future__ import annotations


def draft_letter(product: dict, problem: str, sender_name: str = "") -> str:
    name = product.get("name") or "המוצר"
    model = product.get("model") or ""
    purchase = product.get("purchase_date") or "[תאריך רכישה]"
    model_part = f" (דגם {model})" if model else ""
    signature = sender_name or "[שם מלא]"
    return (
        "לכבוד שירות הלקוחות,\n\n"
        f"הנדון: פנייה בנוגע למוצר {name}{model_part}\n\n"
        f"ברצוני לפנות אליכם בנוגע למוצר שרכשתי בתאריך {purchase}.\n"
        f"תיאור התקלה: {problem.strip() or '[תיאור התקלה]'}\n\n"
        "אבקש לבדוק את האפשרות לתיקון או החלפה במסגרת האחריות. "
        "מצורפים קבלה ותעודת האחריות לפי הצורך.\n\n"
        "תודה מראש,\n"
        f"{signature}\n"
    )
