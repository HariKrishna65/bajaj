import os
import json
import base64
import httpx
from typing import Dict, Any, Tuple


# -------------------------
# SYSTEM_PROMPT MUST BE HERE
# -------------------------
SYSTEM_PROMPT = """
Extract bill line items EXACTLY as required.

Output ONLY JSON, no explanation.

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
- If Qty/Rate missing -> 0.0
- page_type must exactly match.
"""
# -------------------------


def get_api_key():
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


async def extract_page_items_with_llm(input_bytes, page_no, mime="image/png"):
    api_key = get_api_key()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"

    img64 = base64.b64encode(input_bytes).decode("utf-8")

    payload = {
        "contents": [{
            "parts": [
                {"text": SYSTEM_PROMPT},
                {"inline_data": {"mime_type": mime, "data": img64}}
            ]
        }],
        "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
    }

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()

    result = r.json()
    raw = result["candidates"][0]["content"]["parts"][0]["text"].strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    data = json.loads(raw)

    if isinstance(data, list):
        data = {"page_type": "Bill Detail", "bill_items": data}

    data["page_no"] = str(page_no)

    usage = result.get("usageMetadata", {})
    usage_dict = {
        "total_tokens": usage.get("totalTokenCount", 0),
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0),
    }

    return data, usage_dict
