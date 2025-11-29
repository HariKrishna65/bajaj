import json
import os
import base64
import httpx
from typing import Tuple, Dict, Any, Union


# Load Gemini Key
def get_api_key():
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


# -------------------- EXTRACTION RULES --------------------
def enforce_extraction_constraints(page_data: Dict[str, Any]) -> Dict[str, Any]:
    valid_page_types = ["Bill Detail", "Final Bill", "Pharmacy"]

    # Fix page_type
    if "page_type" not in page_data or page_data["page_type"] not in valid_page_types:
        page_type = page_data.get("page_type", "").strip().lower()
        for v in valid_page_types:
            if v.lower() == page_type:
                page_data["page_type"] = v
                break
        else:
            page_data["page_type"] = "Bill Detail"

    # Ensure bill_items exists
    if "bill_items" not in page_data:
        page_data["bill_items"] = []

    # Fix each item
    for item in page_data["bill_items"]:

        # item_name
        if "item_name" not in item:
            item["item_name"] = ""

        # item_rate
        try:
            item["item_rate"] = float(item.get("item_rate", 0.0))
        except:
            item["item_rate"] = 0.0

        # item_quantity
        try:
            item["item_quantity"] = float(item.get("item_quantity", 0.0))
        except:
            item["item_quantity"] = 0.0

        # item_amount (exact value)
        try:
            item["item_amount"] = float(item.get("item_amount", 0.0))
        except:
            item["item_amount"] = 0.0

    return page_data


# -------------------- SYSTEM PROMPT --------------------
SYSTEM_PROMPT = """
Extract bill line items EXACTLY as specified.
Return ONLY JSON and nothing else.

Required structure:
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

Follow rules:
- No totals, tax, discounts.
- Only line items.
- No rounding item_amount.
- If Qty/Rate missing => 0.0
- page_type must match exactly one of required.
- Output STRICT JSON only.
"""


# -------------------- MAIN EXTRACTOR --------------------
def extract_page_items_with_llm(
    input_data: Union[str, bytes],
    page_no: Union[str, int],
    mime: str = "image/png"
) -> Tuple[Dict[str, Any], Dict[str, int]]:

    api_key = get_api_key()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY or GOOGLE_API_KEY")

    model = "gemini-flash-latest"
    api_version = "v1beta"
    url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent?key={api_key}"

    # ----- Prepare payload -----
    if isinstance(input_data, str):
        payload = {
            "contents": [{
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {"text": f"Extract from URL: {input_data}"}
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }
    else:
        b64 = base64.b64encode(input_data).decode()
        payload = {
            "contents": [{
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {"inline_data": {"mime_type": mime, "data": b64}}
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

    print(f"[GEMINI] Calling {model} for page {page_no}...")

    # -------------------- CALL GEMINI --------------------
    try:
        with httpx.Client(timeout=100.0) as client:
            response = client.post(url, json=payload)

        if response.status_code != 200:
            raise ValueError(f"Gemini error: {response.status_code} → {response.text[:200]}")

        data = response.json()

        # Validate structure
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini returned no candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise ValueError("Gemini returned empty content parts")

        text = parts[0].get("text", "").strip()
        if not text:
            raise ValueError("Gemini returned blank text")

        # Clean code blocks
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()

        # Safe JSON parsing
        try:
            page_data = json.loads(text)
        except Exception as err:
            print("\n----- RAW GEMINI OUTPUT START -----")
            print(text)
            print("----- RAW GEMINI OUTPUT END -----\n")
            raise ValueError(f"Gemini invalid JSON: {err}")

        # Add page_no
        page_data["page_no"] = str(page_no)

        # Apply constraints
        print("[GEMINI] Applying constraints...")
        page_data = enforce_extraction_constraints(page_data)

        # Token usage
        usage = {
            "total_tokens": data.get("usageMetadata", {}).get("totalTokenCount", 0),
            "input_tokens": data.get("usageMetadata", {}).get("promptTokenCount", 0),
            "output_tokens": data.get("usageMetadata", {}).get("candidatesTokenCount", 0),
        }

        print(f"[GEMINI] ✓ Success page {page_no} (tokens: {usage['total_tokens']})")
        return page_data, usage


    # -------------------- SAFE ERROR HANDLING (NO CRASH) --------------------
    except Exception as e:
        print(f"[GEMINI] ERROR on page {page_no}: {e}")

        # Return EMPTY PAGE so main API never crashes
        return {
            "page_no": str(page_no),
            "page_type": "Bill Detail",
            "bill_items": []
        }, {
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0
        }
