import json
import os
import base64
import httpx
from typing import Tuple, Dict, Any, Union


def get_api_key():
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def enforce_extraction_constraints(page_data: Dict[str, Any]) -> Dict[str, Any]:
    valid_page_types = ["Bill Detail", "Final Bill", "Pharmacy"]

    if "page_type" not in page_data or page_data["page_type"] not in valid_page_types:
        page_type = page_data.get("page_type", "").strip()
        for valid_type in valid_page_types:
            if page_type.lower() == valid_type.lower():
                page_data["page_type"] = valid_type
                break
        else:
            page_data["page_type"] = "Bill Detail"

    if "bill_items" not in page_data:
        page_data["bill_items"] = []

    for item in page_data["bill_items"]:

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

        # item_amount
        try:
            item["item_amount"] = float(item.get("item_amount", 0.0))
        except:
            item["item_amount"] = 0.0

        # item_name
        if "item_name" not in item:
            item["item_name"] = ""

    return page_data


SYSTEM_PROMPT = """
You are an expert medical bill analyzer...
(Keeping original SYSTEM_PROMPT unchanged)
"""


def extract_page_items_with_llm(
    input_data: Union[str, bytes],
    page_no: Union[str, int],
    mime: str = "image/png"
) -> Tuple[Dict[str, Any], Dict[str, int]]:

    api_key = get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set")

    api_version = "v1beta"
    model_name = "gemini-flash-latest"

    url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model_name}:generateContent?key={api_key}"

    # Prepare payload
    if isinstance(input_data, str):
        payload = {
            "contents": [{
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {"text": f"Extract line items from this document URL: {input_data}"}
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }
    else:
        image_base64 = base64.b64encode(input_data).decode('utf-8')
        payload = {
            "contents": [{
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime,
                            "data": image_base64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

    print(f"[GEMINI API] Calling model: {model_name} for page {page_no}...")

    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(url, json=payload)

        if response.status_code != 200:
            raise ValueError(
                f"Gemini API Error {response.status_code}: {response.text[:300]}"
            )

        result = response.json()

        content = result["candidates"][0]["content"]["parts"][0]["text"]
        raw_text = content.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        page_data = json.loads(raw_text)
        page_data["page_no"] = str(page_no)

        print("[GEMINI API] Applying extraction constraints...")
        page_data = enforce_extraction_constraints(page_data)

        usage_info = result.get("usageMetadata", {})
        usage = {
            "total_tokens": usage_info.get("totalTokenCount", 0),
            "input_tokens": usage_info.get("promptTokenCount", 0),
            "output_tokens": usage_info.get("candidatesTokenCount", 0),
        }

        print(f"[GEMINI API] ✓ Success (tokens: {usage['total_tokens']})")
        return page_data, usage

    except Exception as e:
        raise ValueError(f"Failure with model {model_name}: {str(e)}")
