import os
import json
import base64
import httpx
from typing import Dict, Any, Tuple


# -------------------------
# SYSTEM PROMPT
# -------------------------
SYSTEM_PROMPT = """
Extract bill line items EXACTLY as required.

Output ONLY JSON.

JSON FORMAT:
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
- No totals, tax, discounts.
- Only extract line items.
- No rounding item_amount.
- If Qty or Rate missing -> 0.0
- page_type must exactly match.
"""
# -------------------------


def get_api_key():
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def enforce_constraints(page_data: Dict[str, Any]) -> Dict[str, Any]:
    # Fix page_type
    valid = ["Bill Detail", "Final Bill", "Pharmacy"]
    if page_data.get("page_type") not in valid:
        page_data["page_type"] = "Bill Detail"

    # Fix bill items
    for item in page_data.get("bill_items", []):
        item["item_name"] = item.get("item_name", "")
        item["item_rate"] = float(item.get("item_rate") or 0.0)
        item["item_quantity"] = float(item.get("item_quantity") or 0.0)
        item["item_amount"] = float(item.get("item_amount") or 0.0)

    return page_data


async def extract_page_items_with_llm(input_bytes: bytes, page_no: str, mime="image/png"):

    api_key = get_api_key()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-flash-latest:generateContent?key={api_key}"
    )

    img64 = base64.b64encode(input_bytes).decode("utf-8")

    payload = {
        "contents": [{
            "parts": [
                {"text": SYSTEM_PROMPT},
                {"inline_data": {"mime_type": mime, "data": img64}}
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "response_mime_type": "application/json"
        }
    }

    print(f"[GEMINI] Processing page {page_no}...")

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()

    result = resp.json()
    raw = result["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Clean JSON
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(raw)
    except Exception:
        print("[ERROR] Gemini returned invalid JSON:", raw)
        data = {"page_type": "Bill Detail", "bill_items": []}

    # If list returned → wrap
    if isinstance(data, list):
        data = {"page_type": "Bill Detail", "bill_items": data}

    data["page_no"] = str(page_no)

    data = enforce_constraints(data)

    usage = result.get("usageMetadata", {})
    usage_dict = {
        "total_tokens": usage.get("totalTokenCount", 0),
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0),
    }

    return data, usage_dict
