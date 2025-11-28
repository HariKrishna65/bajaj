import json
import os
import base64
import httpx
from typing import Tuple, Dict, Any, Union

# Read GEMINI key from environment
def get_api_key():
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def enforce_extraction_constraints(page_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforce the extraction constraints on the page data:
    1. If item_rate is not present, set item_rate = 0.0
    2. If item_quantity is not present, set item_quantity = 0.0
    3. Item amount must be exactly as extracted (no rounding)
    4. page_type must be exactly one of: Bill Detail, Final Bill, Pharmacy
    """
    # Validate and fix page_type
    valid_page_types = ["Bill Detail", "Final Bill", "Pharmacy"]
    if "page_type" not in page_data or page_data["page_type"] not in valid_page_types:
        # Try to match case-insensitively or set default
        page_type = page_data.get("page_type", "").strip()
        matched = False
        for valid_type in valid_page_types:
            if page_type.lower() == valid_type.lower():
                page_data["page_type"] = valid_type
                matched = True
                break
        if not matched:
            # Default to "Bill Detail" if can't determine
            page_data["page_type"] = "Bill Detail"
    
    # Validate and fix bill_items
    if "bill_items" not in page_data:
        page_data["bill_items"] = []
    
    for item in page_data["bill_items"]:
        # Rule 1: If item_rate is not present, set item_rate = 0.0
        if "item_rate" not in item or item["item_rate"] is None:
            item["item_rate"] = 0.0
        else:
            # Ensure it's a float
            try:
                item["item_rate"] = float(item["item_rate"])
            except (ValueError, TypeError):
                item["item_rate"] = 0.0
        
        # Rule 2: If item_quantity is not present, set item_quantity = 0.0
        if "item_quantity" not in item or item["item_quantity"] is None:
            item["item_quantity"] = 0.0
        else:
            # Ensure it's a float
            try:
                item["item_quantity"] = float(item["item_quantity"])
            except (ValueError, TypeError):
                item["item_quantity"] = 0.0
        
        # Rule 3: Item amount must be exact (no rounding)
        if "item_amount" in item and item["item_amount"] is not None:
            try:
                # Preserve as float, don't round
                item["item_amount"] = float(item["item_amount"])
            except (ValueError, TypeError):
                # If invalid, set to 0.0
                item["item_amount"] = 0.0
        
        # Ensure item_name exists
        if "item_name" not in item:
            item["item_name"] = ""
    
    return page_data

SYSTEM_PROMPT = """
You are an expert medical bill analyzer.

Extract ONLY the line items from the bill image.

Return ONLY this JSON structure:

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

IMPORTANT RULES (MANDATORY):
1. If item_rate is not present, set item_rate = 0.0
2. If item_quantity is not present, set item_quantity = 0.0
3. Item amount needs to be exactly extracted as present in the document. NO rounding off allowed.
4. page_type must always be exactly one of: Bill Detail, Final Bill, Pharmacy

ADDITIONAL RULES:
- Do NOT include: subtotal, total, tax, discount, headers, notes
- item_name: EXACT text from document
- item_amount: EXACT value from document, preserve all decimal places
- If no items exist, return empty array
- ONLY JSON OUTPUT, no explanation

VALIDATION:
- page_type must be EXACTLY "Bill Detail" OR "Final Bill" OR "Pharmacy" (case-sensitive)
- item_rate: Use 0.0 if not present, otherwise exact value
- item_quantity: Use 0.0 if not present, otherwise exact value
- item_amount: Exact value from document, no rounding, no approximation
"""


def extract_page_items_with_llm(
    input_data: Union[str, bytes],
    page_no: Union[str, int],
    mime: str = "image/png"
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """
    Extract bill items using Gemini AI.
    
    Args:
        input_data: Can be either:
            - URL string (str) - URL to PDF/image
            - Image bytes (bytes) - Direct image data
        page_no: Page number (str or int)
        mime: MIME type (default: "image/png")
    
    Returns:
        Tuple of (page_data dict, usage dict)
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set")
    
    # Try different model names via REST API
    api_version = "v1beta"
    model_names = [
        "gemini-2.0-flash",      # Fast and efficient
        "gemini-2.5-flash",      # Latest flash model
        "gemini-flash-latest",   # Auto-updates to latest
    ]
    
    url_template = f"https://generativelanguage.googleapis.com/{api_version}/models/{{model}}:generateContent?key={{key}}"
    
    # Prepare payload based on input type
    if isinstance(input_data, str):
        # URL input - Gemini can fetch from URLs
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
        # Image bytes input
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
    
    # Try each model until one works
    last_error = None
    for model_name in model_names:
        try:
            url = url_template.format(model=model_name, key=api_key)
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        content = result['candidates'][0]['content']['parts'][0]['text']
                        
                        # Cleanup formatting if Gemini adds code blocks
                        raw_text = content.strip()
                        if raw_text.startswith("```"):
                            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                        
                        page_data = json.loads(raw_text)
                        page_data["page_no"] = str(page_no)
                        
                        # Enforce constraints on the extracted data
                        page_data = enforce_extraction_constraints(page_data)
                        
                        # Extract usage info if available
                        usage_info = result.get('usageMetadata', {})
                        usage = {
                            "total_tokens": usage_info.get('totalTokenCount', 0),
                            "input_tokens": usage_info.get('promptTokenCount', 0),
                            "output_tokens": usage_info.get('candidatesTokenCount', 0)
                        }
                        
                        return page_data, usage
                elif response.status_code == 404:
                    # Model not found, try next one
                    continue
                else:
                    error_text = response.text[:300] if hasattr(response, 'text') else str(response.content[:300])
                    last_error = f"{model_name}: API error ({response.status_code}) - {error_text}"
                    continue
        except json.JSONDecodeError as e:
            last_error = f"{model_name}: JSON decode error - {str(e)}"
            continue
        except Exception as e:
            last_error = f"{model_name}: Exception - {str(e)[:200]}"
            continue
    
    raise ValueError(f"Could not process with any model. Last error: {last_error}")
