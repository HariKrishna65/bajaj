import os
import json
import base64
import httpx
from typing import Dict, Any, Tuple

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
MODEL_NAME = "gemini-2.0-flash-lite"


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
- Missing Qty/Rate → 0.0
- page_type must match exactly.
"""


def enforce_constraints(data: Dict[str, Any]):

    if data.get("page_type") not in ["Bill Detail", "Final Bill", "Pharmacy"]:
        data["page_type"] = "Bill Detail"

    final_items = []
    for item in data.get("bill_items", []):
        final_items.append({
            "item_name": item.get("item_name", ""),
            "item_amount": float(item.get("item_amount") or 0.0),
            "item_rate": float(item.get("item_rate") or 0.0),
            "item_quantity": float(item.get("item_quantity") or 0.0),
        })

    data["bill_items"] = final_items
    return data


async def extract_page_items_with_llm(img_bytes: bytes, page_no: int) -> Tuple[Dict[str, Any], Dict[str, int]]:

    img_b64 = base64.b64encode(img_bytes).decode()

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL_NAME}:generateContent?key={API_KEY}"
    )

    payload = {
        "contents": [{
            "parts": [
                {"text": SYSTEM_PROMPT},
                {"inline_data": {"mime_type": "image/png", "data": img_b64}}
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "response_mime_type": "application/json"
        }
    }

    print(f"[GEMINI] Calling {MODEL_NAME} for page {page_no}...")

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()

    result = r.json()
    txt = result["candidates"][0]["content"]["parts"][0]["text"].strip()

    if txt.startswith("```"):
        txt = txt.replace("```json", "").replace("```", "").strip()

    data = json.loads(txt)
    data["page_no"] = str(page_no)

    data = enforce_constraints(data)

    usage = result.get("usageMetadata", {})
    token_usage = {
        "total_tokens": usage.get("totalTokenCount", 0),
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0)
    }

    return data, token_usage
