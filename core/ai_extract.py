"""Extract product details from a receipt or warranty document with the Claude API.

The model is asked for JSON only. Anything missing or unparseable becomes None;
nothing is guessed. The UI must show every field for user confirmation.
"""
from __future__ import annotations

import base64
import json
import os
import re
from datetime import date

from core.storage import media_type_for

DEFAULT_MODEL = "claude-sonnet-5-5"

PROMPT = """You are reading a receipt or warranty card for a consumer product.
Return ONLY a JSON object with these keys (use null when a value is not clearly present; never guess):
{
  "name": product name as written, string or null,
  "brand": string or null,
  "model": model number, string or null,
  "store": store/seller name, string or null,
  "price": number (no currency symbol), or null,
  "currency": "ILS" | "USD" | "EUR" | other ISO code, or null,
  "purchase_date": "YYYY-MM-DD", or null,
  "warranty_months": integer number of months of warranty, or null,
  "warranty_text": short quote of the warranty terms if present, or null
}
Do not add commentary. Output JSON only."""


def model_name() -> str:
    return os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)


def _block_for(content: bytes, relative_path: str) -> dict:
    media = media_type_for(relative_path)
    encoded = base64.standard_b64encode(content).decode("ascii")
    kind = "document" if media == "application/pdf" else "image"
    return {"type": kind, "source": {"type": "base64", "media_type": media, "data": encoded}}


def extract_from_file(content: bytes, relative_path: str, client=None) -> dict:
    """Call Claude with the file and return a normalized dict of fields."""
    if client is None:
        import anthropic  # imported lazily so tests do not need the SDK call path

        client = anthropic.Anthropic()
    response = client.messages.create(
        model=model_name(),
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": [_block_for(content, relative_path), {"type": "text", "text": PROMPT}],
        }],
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    return parse_extraction(text)


def _json_object(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _text(value) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _number(value) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d.]", "", value)
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    return None


def _date(value) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip()[:10]).isoformat()
    except ValueError:
        return None


def parse_extraction(text: str) -> dict:
    """Turn model output into a clean dict. Invalid values become None."""
    raw = _json_object(text)
    months = _number(raw.get("warranty_months"))
    return {
        "name": _text(raw.get("name")),
        "brand": _text(raw.get("brand")),
        "model": _text(raw.get("model")),
        "store": _text(raw.get("store")),
        "price": _number(raw.get("price")),
        "currency": _text(raw.get("currency")),
        "purchase_date": _date(raw.get("purchase_date")),
        "warranty_months": int(months) if months and months > 0 else None,
        "warranty_text": _text(raw.get("warranty_text")),
    }
