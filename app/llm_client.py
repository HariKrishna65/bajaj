import os
import json
import base64
import httpx
from typing import Dict, Any, Tuple


def get_api_key():
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


SYSTEM_PROMPT = """
Extract only BILL LINE ITEMS from the provided page.

Return ONLY JSON.

FORMAT:
{
  "page_no": "string",
  "page_type": "Bill Detail | Final Bill | Pharmacy",
  "bill_items": [
    {
      "item_name": "string",
      "item_amount": float,
      "item_rate": float,
      "item_quantity": float
    }
  ]
}

RULES:
- Extract ONLY true line items in the bill table.
- Do NOT include totals, GST, discounts, summary, headings.
- item_amount must be EXACT (no rounding).
- If a value is missing → 0.0
- If page has no bill table → return bill_items: []
- page_type must match valid values.
"""


def enforce_constraints(data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean & validate extracted JSON"""
    valid_types = ["Bill Detail", "Final Bill", "Pharmacy"]

    # Fix page_type
    if data.get("page_type") not in valid_types:
        data["page_type"] = "Bill Detail"

    items = data.get("bill_items", [])

    # ❌ Case 1: Page has no valid items → return empty list
    if items is None or items == []:
        data["bill_items"] = []
        return data

    # ❌ Case 2: Model returned a single empty row → remove it
    if len(items) == 1 and not items[0].get("item_name"):
        data["bill_items"] = []
        return data

    cleaned = []

    for item in items:
        name = item.get("item_name", "").strip()

        # Skip blank rows
        if name == "":
            continue

        cleaned.append({
            "item_name": name,
            "item_amount": float(item.get("item_amount") or 0.0),
            "item_rate": float(item.get("item_rate") or 0.0),
            "item_quantity": float(item.get("item_quantity") or 0.0)
        })

    data["bill_items"] = cleaned
    return data


def extract_page_items_with_llm(img_bytes: bytes, page_no: int) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Call Gemini Flash Latest for extraction"""
    api_key = get_api_key()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY")

    model = "gemini-flash-latest"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    img64 = base64.b64encode(img_bytes).decode()

    payload = {
        "contents": [{
            "parts": [
                {"text": SYSTEM_PROMPT},
                {"inline_data": {"mime_type": "image/png", "data": img64}}
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "response_mime_type": "application/json"
        }
    }

    print(f"[GEMINI] Page {page_no} → {model}")

    with httpx.Client(timeout=60) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()

    result = r.json()
    raw = result["candidates"][0]["content"]["parts"][0]["text"]

    # Remove ```json formatting
    txt = raw.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(txt)

    # If model returns a list → auto-wrap
    if isinstance(parsed, list):
        parsed = {
            "page_no": str(page_no),
            "page_type": "Bill Detail",
            "bill_items": parsed
        }
    else:
        parsed["page_no"] = str(page_no)

    # Apply safe cleanup
    parsed = enforce_constraints(parsed)

    usage = result.get("usageMetadata", {})
    return parsed, {
        "total_tokens": usage.get("totalTokenCount", 0),
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0),
    }
