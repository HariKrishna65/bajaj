import os
import json
import base64
import httpx
from typing import Dict, Any, Tuple


# -------------------------------------------------------
# Load API Key
# -------------------------------------------------------
def get_api_key():
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


# -------------------------------------------------------
# System Prompt (minimal + fast)
# -------------------------------------------------------
SYSTEM_PROMPT = """
Extract ONLY bill line items in strict JSON:

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
- No totals, no GST, no discounts, no summary.
- item_amount must be EXACT.
- If qty or rate missing → 0.0
- page_type must match allowed values.
"""


# -------------------------------------------------------
# Cleanup extracted data
# -------------------------------------------------------
def enforce_constraints(data: Dict[str, Any]) -> Dict[str, Any]:
    valid_types = ["Bill Detail", "Final Bill", "Pharmacy"]

    # Fix page_type
    if data.get("page_type") not in valid_types:
        data["page_type"] = "Bill Detail"

    fixed_items = []
    for item in data.get("bill_items", []):
        fixed_items.append({
            "item_name": item.get("item_name", "") or "",
            "item_amount": float(item.get("item_amount") or 0.0),
            "item_rate": float(item.get("item_rate") or 0.0),
            "item_quantity": float(item.get("item_quantity") or 0.0),
        })

    data["bill_items"] = fixed_items
    return data


# -------------------------------------------------------
# Main LLM Extraction Function
# -------------------------------------------------------
def extract_page_items_with_llm(img_bytes: bytes, page_no: int) -> Tuple[Dict[str, Any], Dict[str, int]]:
    api_key = get_api_key()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY")

    # Fastest Gemini model
    model = "gemini-2.0-flash-lite"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    # Encode PNG
    img64 = base64.b64encode(img_bytes).decode()

    # LLM Payload
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

    print(f"[GEMINI FAST] Processing Page {page_no} via {model}")

    # Call Gemini
    with httpx.Client(timeout=40) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()

    result = r.json()

    # Extract JSON text from Gemini
    text = result["candidates"][0]["content"]["parts"][0]["text"]
    text = text.strip().replace("```json", "").replace("```", "").strip()

    # Parse JSON
    data = json.loads(text)

    # ---------------------------------------------------
    # FIX: If model returns a list, auto-wrap to object
    # ---------------------------------------------------
    if isinstance(data, list):
        data = {
            "page_no": str(page_no),
            "page_type": "Bill Detail",
            "bill_items": data
        }
    else:
        data["page_no"] = str(page_no)

    # Apply sanitization rules
    data = enforce_constraints(data)

    # Token usage
    usage = result.get("usageMetadata", {})
    token_usage = {
        "total_tokens": usage.get("totalTokenCount", 0),
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0),
    }

    return data, token_usage
