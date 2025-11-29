import os
import json
import base64
import httpx
from typing import Dict, Any, Tuple, Union


def get_api_key():
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


SYSTEM_PROMPT = """
Extract bill line items EXACTLY as required.

Output ONLY JSON. No explanation. No markdown. No extra text.

REQUIRED JSON FORMAT:
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

STRICT EXTRACTION RULES:
- Extract ONLY true bill line items.
- DO NOT extract totals, subtotals, tax, discounts, footer notes, headers.
- item_amount must be EXACT, with NO rounding.
- If Qty or Rate is missing or blank → use 0.0.
- page_type MUST be exactly one of:
    "Bill Detail", "Final Bill", "Pharmacy"
- If the page has NO bill items → return bill_items as an empty list [].
"""


def enforce_extraction_constraints(page_data: Dict[str, Any]) -> Dict[str, Any]:
    valid_page_types = ["Bill Detail", "Final Bill", "Pharmacy"]

    if page_data.get("page_type") not in valid_page_types:
        page_data["page_type"] = "Bill Detail"

    for item in page_data.get("bill_items", []):
        item["item_rate"] = float(item.get("item_rate") or 0.0)
        item["item_quantity"] = float(item.get("item_quantity") or 0.0)
        item["item_amount"] = float(item.get("item_amount") or 0.0)
        item["item_name"] = item.get("item_name", "")

    return page_data


def extract_page_items_with_llm(
    input_bytes: bytes,
    page_no: str,
    mime: str = "image/png"
) -> Tuple[Dict[str, Any], Dict[str, int]]:

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
        "generationConfig": {
            "temperature": 0.1,
            "response_mime_type": "application/json"
        }
    }

    print(f"[GEMINI] Calling gemini-flash-latest for page {page_no}...")

    with httpx.Client(timeout=90) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()

    result = r.json()
    raw = result["candidates"][0]["content"]["parts"][0]["text"]

    # Clean JSON
    txt = raw.strip()
    if txt.startswith("```"):
        txt = txt.replace("```json", "").replace("```", "").strip()

    data = json.loads(txt)

    # Auto-wrap if Gemini returns list instead of dict
    if isinstance(data, list):
        data = {"page_type": "Bill Detail", "bill_items": data}

    data["page_no"] = str(page_no)

    data = enforce_extraction_constraints(data)

    usage = result.get("usageMetadata", {})
    token_usage = {
        "total_tokens": usage.get("totalTokenCount", 0),
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0),
    }

    return data, token_usage
