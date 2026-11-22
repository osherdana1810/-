"""Answer questions about one product's warranty, using only the stored warranty text."""
from __future__ import annotations

from core.ai_extract import model_name

DISCLAIMER = "זו הסבר כללי בלבד, לא ייעוץ משפטי ולא הבטחה לכיסוי. בדקו תמיד מול תעודת האחריות הרשמית."

SYSTEM = """You help a household understand a product warranty.
Rules:
- Answer ONLY from the warranty text provided. If the text does not answer the question, say you cannot determine it from the document.
- Never promise that a fault is covered. Say what the document says and what is unclear.
- Explain in simple Hebrew unless the user writes in another language.
- Keep answers short."""


def build_context(product: dict) -> str:
    lines = [
        f"מוצר: {product.get('name')}",
        f"יצרן: {product.get('brand') or 'לא ידוע'}",
        f"דגם: {product.get('model') or 'לא ידוע'}",
        f"תאריך רכישה: {product.get('purchase_date') or 'לא ידוע'}",
        f"תקופת אחריות (חודשים): {product.get('warranty_months') or 'לא ידוע'}",
        f"טקסט האחריות: {product.get('warranty_text') or 'לא נשמר טקסט אחריות'}",
    ]
    return "\n".join(lines)


def answer(question: str, product: dict, client=None) -> str:
    if not question.strip():
        return ""
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    response = client.messages.create(
        model=model_name(),
        max_tokens=600,
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": f"{build_context(product)}\n\nשאלה: {question}",
        }],
    )
    text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
    return f"{text.strip()}\n\n_{DISCLAIMER}_"
