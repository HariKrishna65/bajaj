import os
import json
import base64
import httpx
from typing import Dict, Any, Tuple


def get_api_key():
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


SYSTEM_PROMPT = """
Extract bill line items ONLY.

Output strict JSON:
{
  "page_no": "",
  "page_type": "Bill Detail | Final Bill | Pharmacy",
  "bill_items": [
    {
      "item_name": "",
      "item_amount": float,
      "item_rate": float,
      "item_quantity": float
    }
  ]
}

Rules:
- Only real line items.
- No totals/tax/discounts.
- If qty or rate missing → 0.0.
- Amount must be exact.
"""


def enforce_constraints(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize output."""
    valid = ["Bill Detail", "Final Bill", "Pharmacy"]

    if data.get("page_type") not in valid:
        data["page_type"] = "Bill Detail"

    fixed = []
    for item in data.get("bill_items", []):
        fixed.append({
            "item_name": item.get("item_name", "") or "",
            "item_amount": float(item.get("item_amount") or 0.0),
            "item_rate": float(item.get("item_rate") or 0.0),
            "item_quantity": float(item.get("item_quantity") or 0.0),
        })

    data["bill_items"] = fixed
    return data


def extract_page_items_with_llm(img_bytes: bytes, page_no: int) -> Tuple[Dict[str, Any], Dict[str, int]]:
    api_key = get_api_key()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY")

    # FASTEST MODEL
    model = "gemini-2.0-flash-lite"

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

    print(f"[GEMINI FAST] Page {page_no} → {model}")

    with httpx.Client(timeout=40) as client:  # faster timeout
        r = client.post(url, json=payload)
        r.raise_for_status()

    result = r.json()
    txt = result["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Clean JSON
    txt = txt.replace("```json", "").replace("```", "").strip()
    data = json.loads(txt)

    data["page_no"] = str(page_no)
    data = enforce_constraints(data)

    usage = result.get("usageMetadata", {})
    return data, {
        "total_tokens": usage.get("totalTokenCount", 0),
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0)
    }
