import os
import json
import base64
import httpx
from typing import Dict, Any, Tuple


def get_api_key():
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


SYSTEM_PROMPT = """
Extract bill line items EXACTLY as required.

Output ONLY JSON.

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

Rules:
- Extract ONLY real line items.
- Do NOT extract totals, discounts, GST, or summary values.
- item_amount must be EXACT (no rounding).
- If qty/rate missing → 0.0
- page_type must exactly match valid values.
"""


def enforce_constraints(data: Dict[str, Any]) -> Dict[str, Any]:
    valid = ["Bill Detail", "Final Bill", "Pharmacy"]

    if data.get("page_type") not in valid:
        data["page_type"] = "Bill Detail"

    for item in data.get("bill_items", []):
        item["item_name"] = item.get("item_name", "")
        item["item_amount"] = float(item.get("item_amount") or 0.0)
        item["item_rate"] = float(item.get("item_rate") or 0.0)
        item["item_quantity"] = float(item.get("item_quantity") or 0.0)

    return data


def extract_page_items_with_llm(img_bytes: bytes, page_no: int) -> Tuple[Dict[str, Any], Dict[str, int]]:
    api_key = get_api_key()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"

    img64 = base64.b64encode(img_bytes).decode()

    payload = {
        "contents": [{
            "parts": [
                {"text": SYSTEM_PROMPT},
                {"inline_data": {"mime_type": "image/png", "data": img64}}
            ]
        }],
        "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
    }

    print(f"[GEMINI] Page {page_no} → Sending...")

    with httpx.Client(timeout=90) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()

    result = r.json()
    raw = result["candidates"][0]["content"]["parts"][0]["text"]

    txt = raw.strip().replace("```json", "").replace("```", "")
    data = json.loads(txt)
    data["page_no"] = str(page_no)

    data = enforce_constraints(data)

    usage_meta = result.get("usageMetadata", {})
    usage = {
        "total_tokens": usage_meta.get("totalTokenCount", 0),
        "input_tokens": usage_meta.get("promptTokenCount", 0),
        "output_tokens": usage_meta.get("candidatesTokenCount", 0),
    }

    return data, usage
